FROM python:3-alpine

WORKDIR /app

COPY . .

RUN apk add --no-cache curl tar && \
    pip install -r ./requirements.txt && \
    curl https://storage.googleapis.com/<Bucket Name>/env.tar.gz -o - | tar -zxv --no-same-owner -C .
    # Bucket Name: 需填寫指定路徑以布署程式環境

CMD python ./src/webServer.py

