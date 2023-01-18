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

COPY tiptoe ./tiptoe

WORKDIR /code/tiptoe

ARG TIPTOE_DJANGO_SECRET_KEY
ENV TIPTOE_DJANGO_SECRET_KEY=$TIPTOE_DJANGO_SECRET_KEY
ARG TIPTOE_DATABASE_USER
ENV TIPTOE_DATABASE_USER=$TIPTOE_DATABASE_USER
ARG TIPTOE_DATABASE_PASSWORD
ENV TIPTOE_DATABASE_PASSWORD=$TIPTOE_DATABASE_PASSWORD
ARG TIPTOE_DATABASE_HOST
ENV TIPTOE_DATABASE_HOST=$TIPTOE_DATABASE_HOST
ARG TIPTOE_TRIPLESTORE_URL
ENV TIPTOE_TRIPLESTORE_URL=$TIPTOE_TRIPLESTORE_URL

ENV DJANGO_SETTINGS_MODULE=tiptoe.prod_settings
ENTRYPOINT ["gunicorn"]
CMD ["tiptoe.wsgi", "--bind=0.0.0.0:3000", "--workers=2"]
