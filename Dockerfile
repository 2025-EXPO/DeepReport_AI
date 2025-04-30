# 기본 Python 이미지 사용
FROM python:3.11.1

# 작업 디렉토리 설정
WORKDIR /code

# 시스템 패키지 업데이트 및 필요한 패키지 설치
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# requirements.txt 복사 및 의존성 설치
COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir -r /code/requirements.txt

# 프로젝트 파일 복사
COPY ./main.py /code/
COPY ./router /code/router
COPY ./models /code/models
COPY ./database /code/database
COPY ./.env /code/

# 포트 설정 
EXPOSE 8000

# 애플리케이션 실행
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"] 