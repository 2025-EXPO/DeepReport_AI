# main.py
from fastapi import FastAPI
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
import router
from latest_article import fetch_and_store_latest_article
import router.router
import router.sse
import router.gemini
import logging
from router.sse import run_async_job
from fastapi.middleware.cors import CORSMiddleware



logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

executors = {
    'default': {'type': 'threadpool', 'max_workers': 20}
}

scheduler = AsyncIOScheduler(executors=executors)

app = FastAPI()
app.include_router(router.router.router)
app.include_router(router.sse.router)
# app.include_router(router.gemini.router)

origins = [
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get('/')
def get_main():
    return {'message': 'welcome modeep'}

@app.on_event("startup")
async def start_scheduler():
    if not scheduler.running:
        try:
            scheduler.remove_job('news_crawler_job')
        except Exception as e:
            logger.warning(f"기존 작업 제거 중 오류 발생: {e}")
            
        # 동기 래퍼 함수 스케줄링
        scheduler.add_job(
            run_async_job,
            trigger=IntervalTrigger(minutes=30),
            id='news_crawler_job',
            max_instances=1
        )
            
        scheduler.start()
        logger.info("스케줄러 시작: 1분마다 뉴스 크롤링 및 SSE 알림")

@app.on_event("shutdown")
async def shutdown_scheduler():
    if scheduler.running:
        scheduler.shutdown()
        logger.info("스케줄러 종료")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)