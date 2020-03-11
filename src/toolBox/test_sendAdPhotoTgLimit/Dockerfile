
FROM alpine

WORKDIR /app

RUN apk add --no-cache python3 py3-pip && \
    ln -s /usr/bin/python3 /usr/bin/python && \
    ln -s /usr/bin/pip3 /usr/bin/pip

COPY ./requirements.txt .
RUN pip install -r requirements.txt

