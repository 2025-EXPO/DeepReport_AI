from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import requests
from langchain.docstore.document import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_ollama import OllamaEmbeddings
import ollama
import os
import json
import logging
import signal
import sys
import time
from bs4 import BeautifulSoup

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('aitimes_crawler.log'),
        logging.StreamHandler()
    ]
)

class AITimesAgent:
    def __init__(self, start_idx=168551):
        self.base_url = "https://www.aitimes.com/news/articleView.html?idxno="
        self.current_idx = start_idx
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.running = True
        
        # 데이터 저장 디렉토리 생성
        self.json_dir = 'data'
        if not os.path.exists(self.json_dir):
            os.makedirs(self.json_dir)
            logging.info(f"JSON 파일 저장 디렉토리 '{self.json_dir}'를 생성했습니다.")
        
        # Ctrl+C 처리를 위한 시그널 핸들러 등록
        signal.signal(signal.SIGINT, self.signal_handler)
    
    def signal_handler(self, sig, frame):
        """Ctrl+C 신호를 처리하는 함수"""
        logging.info("종료 신호를 받았습니다. 프로그램을 종료합니다...")
        self.running = False
        sys.exit(0)
    
    def check_article_exists(self, soup):
        """기사가 존재하는지 확인하고 알림 유형을 반환"""
        if soup.find(string=lambda text: text and "존재하지 않는 링크" in text):
            return "non_existent"
        
        if soup.find(string=lambda text: text and "노출대기중인 기사" in text):
            return "pending"
            
        title = soup.select_one('h3.heading')
        if not title:
            return "unknown_error"
            
        content_div = soup.select_one('#article-view-content-div')
        if not content_div:
            return "unknown_error"
        
        return "exists"  # 기사가 정상적으로 존재함
    
    def parse_article(self, soup, article_id):
        """기사 정보 파싱"""
        try:
            title = soup.select_one('h3.heading').text.strip()
            content_div = soup.select_one('#article-view-content-div')
            paragraphs = content_div.select('p') if content_div else []
            content = '\n'.join([p.text.strip() for p in paragraphs])
            
            return {
                'id': article_id,
                'title': title,
                'content': content,
                'url': f"{self.base_url}{article_id}",
                'crawled_at': time.strftime("%Y-%m-%d %H:%M:%S")
            }
        except Exception as e:
            logging.error(f"기사 파싱 중 오류 발생 (ID: {article_id}): {str(e)}")
            return None
    
    def crawl_next_article(self):
        """다음 기사 크롤링 시도"""
        url = f"{self.base_url}{self.current_idx}"
        
        try:
            response = requests.get(url, headers=self.headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            article_status = self.check_article_exists(soup)
            
            if article_status == "exists":
                article_data = self.parse_article(soup, self.current_idx)
                return article_data
            
        except Exception as e:
            logging.error(f"ID {self.current_idx} 크롤링 중 오류 발생: {str(e)}")
        
        self.current_idx += 1  # 다음 ID로 이동
        return None

app = FastAPI()

embeddings = OllamaEmbeddings(model="mxbai-embed-large")
vectorstore = Chroma(embedding_function=embeddings)

class ArticleResponse(BaseModel):
    short_summary: str
    medium_summary: str
    long_summary: str

@app.get("/latest_article")
async def get_latest_article():
    # 최신 기사를 크롤링하기 위해 AITimesAgent 인스턴스 생성
    agent = AITimesAgent(start_idx=168540)  # 적절한 시작 인덱스를 설정
    article_data = agent.crawl_next_article()  # 최신 기사 크롤링

    if article_data:
        # 크롤링한 기사 내용에서 본문을 추출
        content = article_data['content']
        
        # 요약 처리
        docs = [Document(page_content=content)]
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        splits = text_splitter.split_documents(docs)
        vectorstore.add_documents(splits)

        retrieved_docs = vectorstore.similarity_search(content)
        if not retrieved_docs:
            return JSONResponse(content={"error": "관련 문서를 찾을 수 없습니다."})

        formatted_context = "\n\n".join(doc.page_content for doc in retrieved_docs)

        short_summary = ollama.chat(model='llama3',
                                     messages=[
                                         {"role": "system", "content": "Please summarize the following text briefly in Korean."},
                                         {"role": "user", "content": formatted_context}])['message']['content']

        medium_summary = ollama.chat(model='llama3',
                                      messages=[
                                          {"role": "system", "content": "Please summarize the following text in Korean."},
                                          {"role": "user", "content": formatted_context}])['message']['content']

        long_summary = ollama.chat(model='llama3',
                                    messages=[
                                        {"role": "system", "content": "Please summarize the following text in detail in Korean."},
                                        {"role": "user", "content": formatted_context}])['message']['content']

        return ArticleResponse(short_summary=short_summary, medium_summary=medium_summary, long_summary=long_summary)
    else:
        return JSONResponse(content={"error": "최신 기사를 찾을 수 없습니다."})

# 메인 실행 코드
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
