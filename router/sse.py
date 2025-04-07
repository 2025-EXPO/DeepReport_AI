
from fastapi import Request, APIRouter
from fastapi.responses import StreamingResponse
import asyncio
import json
from datetime import datetime
from latest_article import fetch_and_store_latest_article
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

clients = set()

async def send_event_to_clients(event_data):
    dead_clients = set()
    for client in clients:
        try:
            await client.put(event_data)
        except Exception:
            dead_clients.add(client)
    clients.difference_update(dead_clients)

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
 
    try:
        is_new_article = await fetch_and_store_latest_article()
        
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

def run_async_job():

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(check_and_notify_new_articles())
    finally:
        loop.close()
