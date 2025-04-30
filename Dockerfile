FROM python:3.11.1

WORKDIR /code

ARG DATABASE_URL
ENV DATABASE_URL=${DATABASE_URL}

ARG SECRET_KEY
ENV SECRET_KEY=${SECRET_KEY}

ARG ACCESS_TOKEN_EXPIRES_MINUTES
ENV ACCESS_TOKEN_EXPIRES_MINUTES=${ACCESS_TOKEN_EXPIRES_MINUTES}

RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir -r /code/requirements.txt

RUN pip install python-dotenv

COPY . /code/

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
