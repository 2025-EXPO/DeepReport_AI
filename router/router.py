from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from database import get_db
from models import Article
from typing import List
import logging

router = APIRouter()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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
    articles = db.query(Article).offset(skip).limit(10).all()  
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



