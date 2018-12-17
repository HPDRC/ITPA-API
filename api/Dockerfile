FROM python:3.6-alpine

RUN apk update
#RUN apt-get update -y && apt-get install -y python-pip python-dev

RUN mkdir -p /api
WORKDIR /api

COPY requirements.txt /api
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

COPY ./code/ /api/code/

EXPOSE ${API_PORT}

WORKDIR /api/code

# Forward logs to Docker
#RUN mkdir /logs
#RUN ln -sf /dev/stdout /logs/access.log && ln -sf /dev/stderr /logs/error.log

ENTRYPOINT [ "gunicorn", "--bind", "0.0.0.0:8000", "--log-level", "info", "wsgi" ]

#ENTRYPOINT [ "python", "-u", "app.py" ]
#CMD [ "app.py" ]
