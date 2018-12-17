FROM mariadb:latest
MAINTAINER Leonard Bay <leonardbay@gmail.com>

COPY config/init.sql /docker-entrypoint-initdb.d/

CMD ["mysqld"]
