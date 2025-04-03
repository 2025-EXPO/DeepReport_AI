# main.py
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
import logging
import asyncio
import json
from datetime import datetime
import router
# latest_article.py에서 함수 임포트
from latest_article import fetch_and_store_latest_article
import router.router
import router.sse

app = FastAPI()
app.include_router(router.router.router)
app.include_router(router.sse.router)



@app.get('/')
def get_main():
    return {'message': 'welcome modeep'}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)