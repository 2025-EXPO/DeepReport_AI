from sqlalchemy.orm import sessionmaker
from database.database import engine
from models.models import Article
import os
import google.generativeai as genai
import re
from src.news import AITimesAgent
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
from src.process_database import remove_partial_duplicate_articles

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

genai.configure(api_key=os.getenv("GEMINI_KEY"))
model = genai.GenerativeModel('gemini-2.0-flash')

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
thread_pool = ThreadPoolExecutor(max_workers=5)

def get_next_index_from_db() -> int:
    db = SessionLocal()
    try:
        last_article = db.query(Article).order_by(Article.current_index.desc()).first()
        if last_article:
            return last_article.current_index + 1
        else:
            return 169400
    finally:
        db.close()

current_index = get_next_index_from_db()
print(current_index)

def generate_with_google(prompt: str) -> str:
    try:
        response = model.generate_content(prompt)
        return response.text.strip() if response else "GEMINI API error"
    except Exception as e:
        logger.error(f"Google API 호출 중 오류 발생: {e}")
        return "API 호출 중 오류 발생"

def clean_text(text: str) -> str:
    return re.sub(r'\s+', ' ', text.replace('\n', ' ').replace('\\', '').replace('**', ' ').replace('"', '').replace('*', '').strip())

async def run_in_thread(func, *args, **kwargs):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(thread_pool, func, *args, **kwargs)

def crawl_with_agent(agent):
    try:
        return agent.crawl_next_article()
    except Exception as e:
        logger.error(f"크롤링 중 오류 발생: {e}")
        return None

async def fetch_and_store_latest_article():
    global current_index
    remove_partial_duplicate_articles()
    
    try:
        agent = AITimesAgent(start_idx=current_index)
        
        for _ in range(3):  
            article_data = await run_in_thread(crawl_with_agent, agent)
            
            if not article_data:
                current_index += 1
                continue
            
            base_url = agent.base_url + str(current_index)
            news_title = clean_text(article_data.get("title", "제목 없음"))
            content = clean_text(article_data['content'])
            
            news_content = clean_text(await run_in_thread(
                generate_with_google, 
                f"{content} Summarize the following text in Korean using only key point-based declarative sentences. Start directly with the summary—no introductory sentences."
            ))
            
            tag = clean_text(await run_in_thread(
                generate_with_google, 
                f"이 뉴스 기사에서 관련된 키워드 5개를 추출하세요. 콤마로 구분된 키워드만 출력하세요: {content}"
            ))
            
            db = SessionLocal()
            try:
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
        
        return False 
    except Exception as e:
        logger.error(f"크롤링 중 오류 발생: {e}")
        return False