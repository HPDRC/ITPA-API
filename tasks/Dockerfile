FROM python:3.6-alpine

RUN pip install --upgrade pip

COPY ./requirements.txt /app/requirements.txt
WORKDIR /app
RUN pip install -r requirements.txt

COPY ./code/ /app/code/
WORKDIR /app/code

ENTRYPOINT celery -A tasks worker --beat --loglevel=warning
