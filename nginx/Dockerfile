FROM nginx:alpine

EXPOSE 80
EXPOSE 443

COPY localhost.crt /etc/ssl/certs/localhost.crt
COPY localhost.key /etc/ssl/private/localhost.key
COPY nginx.conf /etc/nginx/nginx.conf

#RUN mkdir -p /www
#COPY ./index.html /www/

