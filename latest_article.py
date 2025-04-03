from fastapi import FastAPI
from sqlalchemy.orm import sessionmaker
from database import engine
from models import Article
import os
import google.generativeai as genai
import re
from news import AITimesAgent
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Gemini API 설정
genai.configure(api_key=os.getenv("GEMINI_KEY"))
model = genai.GenerativeModel('gemini-2.0-flash')

# 세션 팩토리 생성
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

current_index = 169290

# 스레드 풀 생성 - 모든 블로킹 작업에 사용
thread_pool = ThreadPoolExecutor(max_workers=5)

def generate_with_google(prompt: str) -> str:
    """Gemini API를 사용하여 콘텐츠 생성"""
    try:
        response = model.generate_content(prompt)
        return response.text.strip() if response else "GEMINI API error"
    except Exception as e:
        logger.error(f"Google API 호출 중 오류 발생: {e}")
        return "API 호출 중 오류 발생"

def clean_text(text: str) -> str:
    """텍스트 정제 함수"""
    return re.sub(r'\s+', ' ', text.replace('\n', ' ').replace('\\', '').replace('**', ' ').replace('"', '').strip())

# 블로킹 함수를 래핑하여 스레드 풀에서 실행하는 함수
async def run_in_thread(func, *args, **kwargs):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(thread_pool, func, *args, **kwargs)

# AITimesAgent를 스레드 안에서 사용하는 함수
def crawl_with_agent(agent, idx):
    try:
        return agent.crawl_next_article()
    except Exception as e:
        logger.error(f"크롤링 중 오류 발생: {e}")
        return None

async def fetch_and_store_latest_article():
    global current_index
    try:
        # AITimesAgent 생성 및 크롤링 작업은 스레드 풀에서 실행
        agent = AITimesAgent(start_idx=current_index)
        
        for _ in range(3):  # 최대 3번 시도
            # 크롤링 작업을 스레드 풀에서 실행
            article_data = await run_in_thread(crawl_with_agent, agent, current_index)
            
            if not article_data:
                current_index += 1
                continue
            
            base_url = agent.base_url + str(current_index)
            news_title = clean_text(article_data.get("title", "제목 없음"))
            content = clean_text(article_data['content'])
            
            # Gemini API 호출도 스레드 풀에서 실행
            news_content = clean_text(await run_in_thread(
                generate_with_google, 
                f"{content} Summarize the following text in detail in Korean using declarative sentences only."
            ))
            
            tag = clean_text(await run_in_thread(
                generate_with_google, 
                f"이 뉴스 기사에서 관련된 키워드 5개를 추출하세요. 콤마로 구분된 키워드만 출력하세요: {content}"
            ))
            
            # 데이터베이스 작업도 스레드 풀에서 실행
            db = SessionLocal()
            try:
                # 데이터베이스 작업을 별도의 함수로 분리하여 스레드 풀에서 실행
                def save_to_db():
                    try:
                        new_article = Article(
                            news_title=news_title,
                            news_content=news_content,
                            current_index=current_index,
                            tag=tag,
                            base_url=base_url
                        )
                        db.add(new_article)
                        db.commit()
                        db.refresh(new_article)
                        return True
                    except Exception as db_error:
                        logger.error(f"데이터베이스 저장 중 오류 발생: {db_error}")
                        db.rollback()
                        return False
                
                success = await run_in_thread(save_to_db)
                if success:
                    logger.info(f"새 기사 저장 완료: {current_index}")
                    current_index += 1
                    return True
                else:
                    return False
            finally:
                db.close()
        
        return False  # 모든 시도가 실패한 경우
    except Exception as e:
        logger.error(f"크롤링 중 오류 발생: {e}")
        return False