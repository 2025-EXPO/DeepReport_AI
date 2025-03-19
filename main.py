from fastapi import FastAPI, Depends
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
from router import router

app = FastAPI()
app.include_router(router)

@app.get('/')
def get_main():
    return{'message' : 'welcome modeep'}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
