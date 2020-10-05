# 最小可用於 K8s 的映像文件

FROM alpine

WORKDIR /app

CMD ["tail", "-f", "/dev/null"]

