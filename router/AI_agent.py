from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from database.database import get_db
from models.models import Article
import os
import google.generativeai as genai
import logging

router = APIRouter()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

genai.configure(api_key=os.getenv("GEMINI_KEY"))
model = genai.GenerativeModel('gemini-2.0-flash')  

def ask_gemini(prompt: str) -> str:
    try:
        response = model.generate_content(prompt)
        return response.text if response else "GEMINI API error"
    except Exception as e:
        logger.error(f"Gemini API 오류: {e}")
        return "API 호출 중 오류 발생"

@router.post("/articles/{article_id}/ask")
def ask_about_article(article_id: int, question: str, db: Session = Depends(get_db)):
    article = db.query(Article).filter(Article.current_index == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="기사 정보를 찾을 수 없습니다.")
    
    prompt = (
        f"다음 뉴스 내용을 참고해서 사용자의 질문에 답변해줘.\n\n"
        f"뉴스 제목: {article.news_title}\n"
        f"뉴스 내용: {article.news_content}\n\n"
        f"사용자 질문: {question}\n"
        f"답변:"
    )


    result = ask_gemini(prompt)
    return JSONResponse(content={"answer": result})
