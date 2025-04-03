# main.py
from fastapi import FastAPI, Request, APIRouter
from fastapi.responses import StreamingResponse
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
import logging
import asyncio
import json
from datetime import datetime
from router.router import router
from latest_article import fetch_and_store_latest_article

router = APIRouter()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ThreadPoolExecutor만 사용
executors = {
    'default': {'type': 'threadpool', 'max_workers': 20}
}

scheduler = AsyncIOScheduler(executors=executors)
clients = set()

async def send_event_to_clients(event_data):
    dead_clients = set()
    for client in clients:
        try:
            await client.put(event_data)
        except Exception:
            dead_clients.add(client)
    clients.difference_update(dead_clients)

@router.get('/')
def get_main():
    return {'message': 'welcome modeep'}

@router.get('/news-notifications')
async def news_notifications(request: Request):
    async def event_generator():
        client_queue = asyncio.Queue()
        clients.add(client_queue)
        
        try:
            yield "data: " + json.dumps({"message": "Connected to news notifications"}) + "\n\n"
            
            while True:
                if await request.is_disconnected():
                    break
                
                try:
                    data = await asyncio.wait_for(client_queue.get(), timeout=1.0)
                    yield f"data: {json.dumps(data)}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            clients.discard(client_queue)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no'
        }
    )

async def check_and_notify_new_articles():
    """
    최신 기사를 크롤링하고 클라이언트에게 알림
    """
    try:
        # 비동기 크롤링 함수 호출
        is_new_article = await fetch_and_store_latest_article()
        
        # 새 기사가 저장되었다면 클라이언트에게 알림
        if is_new_article:
            event_data = {
                "event": "new_article",
                "message": "새로운 기사가 추가되었습니다. API를 통해 조회하세요.",
                "timestamp": datetime.now().isoformat()
            }
            await send_event_to_clients(event_data)
            logger.info(f"새 기사 알림을 {len(clients)}개 클라이언트에게 전송했습니다.")
        else:
            logger.info("새 기사가 없거나 크롤링에 실패했습니다.")
    except Exception as e:
        logger.error(f"크롤링 및 알림 과정에서 오류 발생: {e}")

# 스케줄러에서 실행할 동기 래퍼 함수
def run_async_job():
    """
    비동기 작업을 실행하기 위한 동기 래퍼 함수
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(check_and_notify_new_articles())
    finally:
        loop.close()

@router.on_event("startup")
async def start_scheduler():
    if not scheduler.running:
        try:
            scheduler.remove_job('news_crawler_job')
        except Exception as e:
            logger.warning(f"기존 작업 제거 중 오류 발생: {e}")
            
        # 동기 래퍼 함수 스케줄링
        scheduler.add_job(
            run_async_job,
            trigger=IntervalTrigger(minutes=1),
            id='news_crawler_job',
            max_instances=1
        )
            
        scheduler.start()
        logger.info("스케줄러 시작: 1분마다 뉴스 크롤링 및 SSE 알림")

@router.on_event("shutdown")
async def shutdown_scheduler():
    if scheduler.running:
        scheduler.shutdown()
        logger.info("스케줄러 종료")