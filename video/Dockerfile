FROM ubuntu:trusty

ARG DEBIAN_FRONTEND=noninteractive
ENV PATH $PATH:/usr/local/nginx/sbin

ENV FORCE_CHANGE=0

# create directories
RUN mkdir /src /config /logs /data /static

# update and upgrade packages
RUN apt-get update && \
  apt-get upgrade -y && \
  apt-get clean && \
  apt-get install -y --no-install-recommends build-essential \
  wget software-properties-common && \
# ffmpeg
  add-apt-repository ppa:mc3man/trusty-media && \
  apt-get update && \
  apt-get install -y --no-install-recommends ffmpeg && \
# nginx dependencies
  apt-get install -y --no-install-recommends libpcre3-dev \
  zlib1g-dev libssl-dev wget && \
  rm -rf /var/lib/apt/lists/*

# get nginx source
WORKDIR /src
RUN wget http://nginx.org/download/nginx-1.15.1.tar.gz && \
  tar zxf nginx-1.15.1.tar.gz && \
  rm nginx-1.15.1.tar.gz && \
# get nginx-rtmp module
  wget https://github.com/arut/nginx-rtmp-module/archive/v1.2.1.tar.gz && \
  tar zxf v1.2.1.tar.gz && \
  rm v1.2.1.tar.gz

COPY ./ngx_rtmp_version.h /src/nginx-rtmp-module-1.2.1/

# compile nginx
WORKDIR /src/nginx-1.15.1
RUN ./configure --add-module=/src/nginx-rtmp-module-1.2.1 \
  --conf-path=/config/nginx.conf \
  --error-log-path=/logs/error.log \
  --http-log-path=/logs/access.log && \
  make && \
  make install

# Forward logs to Docker
RUN ln -sf /dev/stdout /logs/access.log && \
    ln -sf /dev/stderr /logs/error.log
RUN ln -sf /dev/stdout /logs/access2.log && \
    ln -sf /dev/stderr /logs/error2.log

WORKDIR /

COPY static /static

COPY nginx.conf /config/nginx.conf

EXPOSE ${VIDEO_RTMP_PORT}
EXPOSE ${VIDEO_APP_PORT}

CMD "nginx"
