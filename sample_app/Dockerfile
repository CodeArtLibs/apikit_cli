ARG APIKIT_IMAGE
FROM ${APIKIT_IMAGE}

# For APIKit CLI testing

# Implicit by base image
# WORKDIR /app
# COPY requirements-app.txt .
# RUN env/bin/pip install -r requirements-app.txt --no-cache-dir
# COPY ./apps* /app/apps

RUN apk add curl nano

ENV API_VERSION=dev

WORKDIR /app
COPY requirements-app.txt .
RUN env/bin/pip install -r requirements-app.txt --no-cache-dir
COPY ./apps* /app/apps

# /app/env/bin/uvicorn api_web.version_server:asgi_app --host 0.0.0.0 --port 50000 --workers 1 --loop uvloop --interface asgi3 --lifespan on --no-server-header --no-date-header
