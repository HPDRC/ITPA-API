FROM node:10.9.0-alpine

ENV FFMPEG_VERSION=3.3.5
RUN apk update && \
    apk upgrade && \
    apk add --update ca-certificates && \
    apk add gnutls-dev zlib-dev yasm-dev lame-dev libogg-dev \
    x264-dev libvpx-dev libvorbis-dev x265-dev freetype-dev \
    libass-dev libwebp-dev rtmpdump-dev libtheora-dev opus-dev && \
    apk add --no-cache --virtual .build-dependencies \
    build-base coreutils tar bzip2 x264 gnutls nasm && \
    wget -O- http://ffmpeg.org/releases/ffmpeg-${FFMPEG_VERSION}.tar.gz | tar xzC /tmp && \
    cd /tmp/ffmpeg-${FFMPEG_VERSION} && \
    ./configure --bindir="/usr/bin" \
                --enable-version3 \
                --enable-gpl \
                --enable-nonfree \
                --enable-small \
                --enable-libmp3lame \
                --enable-libx264 \
                --enable-libx265 \
                --enable-libvpx \
                --enable-libtheora \
                --enable-libvorbis \
                --enable-libopus \
                --enable-libass \
                --enable-libwebp \
                --enable-librtmp \
                --enable-postproc \
                --enable-avresample \
                --enable-libfreetype \
                --enable-gnutls \
                --enable-shared \
                --disable-debug && \
    make && \
    make install && \
    make distclean && \
    cd $OLDPWD && \
    rm -rf /tmp/ffmpeg-${FFMPEG_VERSION} && \
    apk del --purge .build-dependencies && \
    rm -rf /var/cache/apk/*

RUN apk add --no-cache ca-certificates
#RUN apk add --no-cache git build-base musl-dev alpine-sdk cmake clang clang-dev gcc g++ libc-dev linux-headers
RUN apk add --no-cache git build-base musl-dev alpine-sdk cmake clang clang-dev gcc g++ libc-dev linux-headers libpng-dev libjpeg-turbo-dev giflib-dev libx11-dev python util-linux

ENV OPENCV4NODEJS_DISABLE_AUTOBUILD=1

RUN mkdir /tmp/opencv
WORKDIR /tmp/opencv
RUN wget -O opencv.zip https://github.com/opencv/opencv/archive/3.4.1.zip
RUN unzip opencv.zip
RUN wget -O opencv_contrib.zip https://github.com/opencv/opencv_contrib/archive/3.4.1.zip
RUN unzip opencv_contrib.zip
RUN mkdir /tmp/opencv/opencv-3.4.1/build

WORKDIR /tmp/opencv/opencv-3.4.1/build
RUN cmake -D CMAKE_BUILD_TYPE=RELEASE \
    -D CMAKE_INSTALL_PREFIX=/usr/local \
    -D OPENCV_EXTRA_MODULES_PATH=/tmp/opencv/opencv_contrib-3.4.1/modules \
    -D BUILD_DOCS=OFF \
    -D BUILD_EXAMPLES=OFF \
    -D BUILD_TESTS=OFF \
    -D BUILD_PERF_TESTS=OFF \
    -D BUILD_opencv_java=OFF \
    -D BUILD_opencv_python=OFF \
    -D BUILD_opencv_python2=OFF \
    -D BUILD_opencv_python3=OFF \
    -D WITH_IPP=OFF \
    ..

RUN make -j4
RUN make install

RUN rm -rf /tmp/opencv

ENV LD_LIBRARY_PATH=/usr/lib:/usr/local/lib:/usr/local/lib64
ENV PKG_CONFIG_PATH=/usr/lib/pkgconfig:/usr/local/lib/pkgconfig:/usr/local/lib64/pkgconfig

ENV OPENCV_LIB_DIR=/usr/local/lib64
ENV OPENCV_DIR=/usr/local/share/OpenCV
ENV PATH="${OPENCV_LIB_DIR}:${PATH}"

WORKDIR /opencv4nodejs
RUN npm --loglevel=error i opencv4nodejs

WORKDIR /usr/src/app

RUN npm config set unsafe-perm true

RUN npm --no-warnings install -g node-gyp

COPY ./code/package*.json ./
COPY ./addon/ .

RUN npm --no-warnings install
# If you are building your code for production
# RUN npm install --only=production

COPY ./code/ .

#RUN npm --no-warnings install

EXPOSE ${SOCKETIO_PORT}
CMD [ "npm", "start" ]
