from fastapi import Request, APIRouter, Depends
from fastapi.responses import StreamingResponse
import asyncio
import json
from datetime import datetime
from src.latest_article import fetch_and_store_latest_article
import logging
from sqlalchemy.orm import Session
from database.database import get_db
from models.models import Article

router = APIRouter()
logger = logging.getLogger(__name__)

clients = set()

async def send_event_to_clients(event_data):
    dead_clients = set()
    for client in clients:
        try:
            await client.put(event_data)
        except Exception as e:
            logger.warning(f"클라이언트 송신 실패: {e}")
            dead_clients.add(client)
    clients.difference_update(dead_clients)

@router.get('/news-notifications')
async def news_notifications(request: Request):
    async def event_generator():
        client_queue = asyncio.Queue()
        clients.add(client_queue)

        yield "data: " + json.dumps({"message": "Connected to news notifications"}) + "\n\n"

        try:
            while not await request.is_disconnected():
                try:
                    data = await asyncio.wait_for(client_queue.get(), timeout=10.0)
                    yield f"data: {json.dumps(data)}\n\n"
                except asyncio.TimeoutError:
                    # Keepalive ping
                    yield ": keepalive\n\n"
        finally:
            clients.discard(client_queue)
            logger.info("클라이언트 연결 해제됨.")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no'
        }
    )

async def check_and_notify_new_articles(db: Session):
    is_new_article = await fetch_and_store_latest_article()

    if not is_new_article:
        logger.info("새 기사가 없거나 크롤링에 실패했습니다.")
        return

    latest_article = db.query(Article).order_by(Article.current_index.desc()).first()
    if not latest_article:
        logger.warning("DB에서 최신 기사를 찾을 수 없습니다.")
        return

    article_data = {
        "title": latest_article.news_title,
        "id": latest_article.current_index,
        "content": latest_article.news_content,
        "tag": latest_article.tag,
        "url": latest_article.base_url
    }

    event_data = {
        "event": "new_article",
        "message": "새로운 기사가 추가되었습니다. API를 통해 조회하세요.",
        "article": article_data,
        "timestamp": datetime.now().isoformat()
    }

    await send_event_to_clients(event_data)
    logger.info(f"새 기사 알림을 {len(clients)}개 클라이언트에게 전송했습니다.")

def run_async_job():
    """비동기 작업을 새로운 이벤트 루프에서 실행"""
    asyncio.run(run_check_and_notify())

async def run_check_and_notify():
    """비동기 작업용 래퍼 함수"""
    db = next(get_db())
    try:
        await check_and_notify_new_articles(db)
    finally:
        db.close()
