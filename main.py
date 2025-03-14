from fastapi import FastAPI
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

app = FastAPI()

embeddings = OllamaEmbeddings(model="mxbai-embed-large")
vectorstore = Chroma(embedding_function=embeddings)

class ArticleResponse(BaseModel):
    short_summary: str
    medium_summary: str
    current_index: int

current_index = 168559  

@app.get("/latest_article")
async def get_latest_article():
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

        current_index += 1

        return ArticleResponse(short_summary=short_summary, medium_summary=medium_summary, current_index = current_index)
    else:
        return JSONResponse(content={"error": "최신 기사를 찾을 수 없습니다."})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)