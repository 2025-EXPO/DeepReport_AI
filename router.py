from fastapi import APIRouter,Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import requests
from langchain.docstore.document import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_ollama import OllamaEmbeddings
import ollama
from news import AITimesAgent
import re
from sqlalchemy.orm import Session
from database import get_db  
from models import Article  # models.py에서 Article 모델 가져오기

router = APIRouter()

embeddings = OllamaEmbeddings(model="mxbai-embed-large")
vectorstore = Chroma(embedding_function=embeddings)


current_index = 168559  

@router.get("/latest_article")
async def get_latest_article(db: Session = Depends(get_db)):
    global current_index  
    agent = AITimesAgent(start_idx=current_index)
    article_data = agent.crawl_next_article()

    if article_data:
        content = article_data['content']
        
        content = content.replace('\n', ' ').replace('\r', ' ').replace('\\n', ' ').replace('\t', ' ').strip()
        content = re.sub(r'\s+', ' ', content)

        docs = [Document(page_content=content)]
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        splits = text_splitter.split_documents(docs)
        vectorstore.add_documents(splits)

        retrieved_docs = vectorstore.similarity_search(content)
        if not retrieved_docs:
            return JSONResponse(content={"error": "관련 문서를 찾을 수 없습니다."})

        formatted_context = " ".join(doc.page_content for doc in retrieved_docs)

        short_summary = ollama.chat(model='Llama-Koren',
                                     messages=[
                                         {"role": "system", "content": "Summarize the following text briefly in Korean."},
                                         {"role": "user", "content": formatted_context}])['message']['content']

        medium_summary = ollama.chat(model='Llama-Koren',
                                      messages=[
                                          {"role": "system", "content": "Summarize the following text in Korean."},
                                          {"role": "user", "content": formatted_context}])['message']['content']

        short_summary = short_summary.replace('\n', ' ').replace('\\n', ' ').strip()
        medium_summary = medium_summary.replace('\n', ' ').replace('\\n', ' ').strip()

        # 데이터베이스에 저장
        new_article = Article(short_summary=short_summary, medium_summary=medium_summary, current_index=current_index)
        db.add(new_article)
        db.commit()
        db.refresh(new_article)

        current_index += 1

        return Article(short_summary=short_summary, medium_summary=medium_summary, current_index=current_index)
    else:
        return JSONResponse(content={"error": "최신 기사를 찾을 수 없습니다."})
