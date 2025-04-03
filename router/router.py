from fastapi import FastAPI, APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from database import get_db
from models import Article
from typing import List
import os
import google.generativeai as genai
import re
from news import AITimesAgent
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import logging

app = FastAPI()
router = APIRouter()

# 로깅 설정 추가
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

genai.configure(api_key=os.getenv("GEMINI_KEY"))
model = genai.GenerativeModel('gemini-2.0-flash')

current_index = 169050
scheduler = BackgroundScheduler()

def generate_with_google(prompt: str) -> str:
    try:
        response = model.generate_content(prompt)
        return response.text if response else "GEMINI API error"
    except Exception as e:
        logger.error(f"Google API 호출 중 오류 발생: {e}")
        return "API 호출 중 오류 발생"



@router.get("/latest_article")
async def get_latest_article(db: Session = Depends(get_db)):
    global current_index
    agent = AITimesAgent(start_idx=current_index)

    for _ in range(3):  # 최대 3번 시도
        article_data = agent.crawl_next_article()
        base_url = agent.base_url + str(current_index)

        if article_data:
            content = article_data['content']
            content = re.sub(r'\s+', ' ', content.replace('\n', ' ').replace('\r', ' ').strip())

            news_title = generate_with_google(content + "Generate only the title based on the following news article content. in korean")
            news_content = generate_with_google(content + "Summarize the following text in detail in Korean using declarative sentences only.")
            tag = generate_with_google(f"이 뉴스 기사에서 관련된 키워드 5개를 추출하세요. 콤마로 구분된 키워드만 출력하세요: {content}")

            news_title = news_title.replace('\n', ' ').replace('\\n', ' ').replace('\\','').replace('**',' ').replace('\"', '')
            news_content = news_content.replace('\n', ' ').replace('\\n', ' ').replace('\\','').replace('**',' ').replace('\"', '')
            tag = tag.replace('\n', ' ').replace('\\n', ' ').replace('\\','').replace('**',' ')

            new_article = Article(
                news_title=news_title.strip(),
                news_content=news_content.strip(),
                current_index=current_index,
                tag=tag.strip(),
                base_url=base_url.strip()
            )
            db.add(new_article)
            db.commit()
            db.refresh(new_article)

            current_index += 1

            return JSONResponse(content={
                "news_title": news_title.strip(),
                "news_content": news_content.strip(),
                "current_index": current_index - 1,
                "tag": tag.strip(),
                "url": base_url.strip()
            })

        # 뉴스 기사가 없으면 다음 인덱스로 이동
        current_index += 1

    return JSONResponse(content={"error": "최신 기사를 찾을 수 없습니다."})

@router.get("/articles/initial", response_model=List[dict])
async def get_initial_articles(db: Session = Depends(get_db)):
    articles = db.query(Article).limit(10).all()
    article_list = [{
        "title": article.news_title,
        "id": article.current_index,
        "content": article.news_content,
        "tag": article.tag,
        "url": article.base_url
    } for article in articles]
    return JSONResponse(content=article_list)

@router.get("/articles/all", response_model=List[dict])
async def get_all_articles(skip: int = 0, db: Session = Depends(get_db)):
    articles = db.query(Article).offset(skip).limit(10).all()  # 10개씩 가져오기
    article_list = [{
        "title": article.news_title,
        "id": article.current_index,
        "content": article.news_content,
        "tag": article.tag,
        "url": article.base_url
    } for article in articles]
    return JSONResponse(content=article_list)

@router.get("/article/{article_id}")
async def get_article_detail(article_id: int, db: Session = Depends(get_db)):
    article = db.query(Article).filter(Article.current_index == article_id).first()
    if article:
        return JSONResponse(content={
            "title": article.news_title,
            "content": article.news_content,
            "tags": article.tag,
            "url": article.base_url
        })
    else:
        return JSONResponse(content={"error": "해당 기사를 찾을 수 없습니다."})
