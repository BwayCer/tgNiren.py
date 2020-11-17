# 最小可用於 K8s 的映像文件

FROM alpine

WORKDIR /app
RUN apk upgrade --no-cache && \
    apk add --no-cache \
        grep less curl bash bash-completion vim git tmux wget tree && \
    ln -sf /usr/bin/vim /usr/bin/vi

CMD ["tail", "-f", "/dev/null"]

