from fastapi import FastAPI
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
import router
from router.sse import run_async_job
import logging
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

executors = {
    'default': {'type': 'threadpool', 'max_workers': 20}
}
scheduler = AsyncIOScheduler(executors=executors)

@asynccontextmanager
async def lifespan(app: FastAPI):
    if not scheduler.running:
        try:
            scheduler.remove_job('news_crawler_job')
        except Exception as e:
            logger.warning(f"기존 작업 제거 중 오류 발생: {e}")
        
        scheduler.add_job(
            run_async_job,
            trigger=IntervalTrigger(minutes=1),
            id='news_crawler_job',
            max_instances=1
        )
        scheduler.start()
        logger.info("스케줄러 시작: 1분마다 뉴스 크롤링 및 SSE 알림")
    
    yield  

    if scheduler.running:
        scheduler.shutdown()
        logger.info("스케줄러 종료")

app = FastAPI(lifespan=lifespan)

origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router.router.router)
app.include_router(router.sse.router)
# app.include_router(router.gemini.router)

@app.get("/")
def get_main():
    return {"message": "welcome modeep"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
