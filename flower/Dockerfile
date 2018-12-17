FROM python:3.6-alpine

COPY . /flower
WORKDIR /flower

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

ENTRYPOINT flower --broker=redis://:${REDIS_PASSWORD}@${REDIS_HOST}:${REDIS_PORT}/${REDIS_FLOWER_DB} --basic_auth=${CELERY_USER}:${CELERY_PASSWORD}
