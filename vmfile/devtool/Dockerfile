# 開發環境

FROM alpine


## 固定配置

RUN adduser --uid 1000 --disabled-password developer
WORKDIR /app


## 需求配置

RUN apk add --no-cache python3 py3-pip && \
    ln -s /usr/bin/python3 /usr/bin/python && \
    ln -s /usr/bin/pip3 /usr/bin/pip

ENV PIPENV_VENV_IN_PROJECT=1
RUN pip install pipenv

