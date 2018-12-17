FROM python:3.4

ENV PYTHONUNBUFFERED 1
MAINTAINER HPDRC

RUN apt-get update -y
#RUN apt-get upgrade -y
RUN apt-get install -y apt-utils
RUN apt-get install -y binutils libproj-dev gdal-bin libgdal-dev python3-gdal

ENV USER itpa

RUN mkdir -p /usr/src/app
RUN mkdir -p /usr/src/app/itpa
WORKDIR /usr/src/app

COPY requirements.txt /usr/src/app/

RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

COPY docker-entrypoint.sh /usr/src/app/
COPY manage.py /usr/src/app/
COPY ./itpa/ /usr/src/app/itpa/

EXPOSE 8060
ENTRYPOINT ["/bin/bash", "docker-entrypoint.sh"]
