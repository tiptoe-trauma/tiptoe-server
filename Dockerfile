FROM python:3.8.6-alpine

RUN mkdir -p /code

WORKDIR /code

EXPOSE 3000

RUN apk update && \
    apk add --no-cache \
        gcc \
        musl-dev \
        libc-dev \
        linux-headers \
        postgresql-dev

COPY newer_reqs.txt .
RUN pip install -r newer_reqs.txt

RUN pip install gunicorn

COPY cafe ./cafe

WORKDIR /code/cafe

ARG CAFE_DJANGO_SECRET_KEY
ENV CAFE_DJANGO_SECRET_KEY=$CAFE_DJANGO_SECRET_KEY
ARG CAFE_DATABASE_USER
ENV CAFE_DATABASE_USER=$CAFE_DATABASE_USER
ARG CAFE_DATABASE_PASSWORD
ENV CAFE_DATABASE_PASSWORD=$CAFE_DATABASE_PASSWORD
ARG CAFE_DATABASE_HOST
ENV CAFE_DATABASE_HOST=$CAFE_DATABASE_HOST
ARG CAFE_TRIPLESTORE_URL
ENV CAFE_TRIPLESTORE_URL=$CAFE_TRIPLESTORE_URL

ENV DJANGO_SETTINGS_MODULE=cafe.prod_settings
ENTRYPOINT ["gunicorn"]
CMD ["cafe.wsgi", "--bind=0.0.0.0:3000", "--workers=2"]
