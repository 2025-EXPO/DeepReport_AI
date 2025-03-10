import gradio as gr
from langchain.docstore.document import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_ollama import OllamaEmbeddings
import ollama

# 임베딩 모델 초기화
embeddings = OllamaEmbeddings(model="mxbai-embed-large")

# 벡터 저장소 초기화 (embedding_function을 포함)
vectorstore = Chroma(embedding_function=embeddings)

# 입력된 텍스트를 벡터 저장소에 추가하는 함수
def add_article(input_text):
    if not input_text:
        return "입력된 텍스트가 없습니다."

    docs = [Document(page_content=input_text)]
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    splits = text_splitter.split_documents(docs)
    vectorstore.add_documents(splits)  # 임베딩이 자동으로 처리됨
    return "기사 추가 완료."

# RAG 체인을 통한 요약 함수
def rag_summarize(question):
    if not question:
        return "질문이 없습니다."
    
    retrieved_docs = vectorstore.similarity_search(question)  # 관련 문서 검색
    if not retrieved_docs:
        return "관련 문서를 찾을 수 없습니다."
    
    formatted_context = "\n\n".join(doc.page_content for doc in retrieved_docs)
    
    # 요약 모델 사용
    response = ollama.chat(model='llama3',
                           messages=[
                                {"role": "system",
                                 "content": "You are a helpful assistant. Please summarize the following text in Korean."
                                },
                                {"role": "user", "content": formatted_context}])
    
    return response['message']['content']

# Gradio 인터페이스 설정
iface = gr.Interface(
    fn=lambda input_text, question: (add_article(input_text), rag_summarize(question)),
    inputs=[gr.Textbox(label="AI 관련 뉴스 기사", lines=10), gr.Textbox(label="질문")],
    outputs=["text", "text"]
)

iface.launch()
