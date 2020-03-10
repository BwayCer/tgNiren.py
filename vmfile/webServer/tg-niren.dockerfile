# Telegram 小工具服務器

FROM python:3-alpine

WORKDIR /app

COPY . .

RUN pip install -r ./requirements.txt

# 需要於 "envfile" 目錄下建立必要的環境文件
# 建議使用 K8s 的 Persistent Volume Claim
# RUN apk add --no-cache curl tar && \
#     curl https://path/to/env.tar.gz -o - | tar -zxv --no-same-owner -C .

CMD ["python", "./src/webServer.py"]

