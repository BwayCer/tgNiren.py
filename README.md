Telegram Niren
=======


> version： v0.0.0

Use [Telethon](https://github.com/LonamiWebs/Telethon) to operate niren user.



## 使用方式


### Telegram 小工具服務器


```
docker build -t local/devtool:tgNiren -f ./vmfile/devtool/Dockerfile ./vmfile/devtool
alias devtool_tgNiren="docker run -it --network host -v \"$PWD:/app\" local/devtool:tgNiren"

devtool_tgNiren pipenv install

cp ./envfile/env.example.yml ./envfile/env.yml
# edit ./envfile/env.yml
# creat telethon session for Telegram connect

devtool_tgNiren pipenv run ./src/webServer.py
```



### 小工具


```
# 查看命令
./src/tool.py --router
```


**增加小工具：**

```
# vim ./src/toolBox/sayHi.py
# @param args - 命令攜帶參數
# @param _dirpy - 小工具文件所在目錄
# @param _dirname - 起始文件 (./src/tool.py) 所在目錄
def run(args: list, _dirpy: str, _dirname: str):
    print(args)     # ['Ab', 'Cde'[, ...]]
    print(_dirpy)   # /path/to/src/toolBox
    print(_dirname) # /path/to/src

# vim ./src/tool.py
_pyTool = {
    'sayHi': 'toolBox/sayHi', # 相對於 ./src/tool.py 的路徑 (不加附檔名)
}

# 執行命令
./src/tool.py sayHi Ab Cde [...]
```



## Kubernetes 布署


```
# 上傳環境文件
tar -zcvf env.tar.gz ./envfile/env.yml ./envfile/tgSession/telethon-*
gsutil cp env.tar.gz gs://<Bucket Name>/env.tar.gz

# 推送環境容器
# https://cloud.google.com/container-registry/docs/pushing-and-pulling
ln -s ./vmfile/tg-niren/.dockerignore .
docker build -t us.gcr.io/tg-tool/k8small  -f ./vmfile/tg-niren/docker/k8small.dockerfile  ./vmfile/tg-niren
docker build -t us.gcr.io/tg-tool/tg-niren -f ./vmfile/tg-niren/docker/tg-niren.dockerfile .
docker push us.gcr.io/tg-tool/k8small
docker push us.gcr.io/tg-tool/tg-niren

# K8s 布署
./vmfile/tg-niren/bin/k8sketch.sh ./vmfile/tg-niren/k8s/

# kubectl delete deployments <Deployments Name>
# kubectl delete services <Services Name>
# kubectl delete ingresses <Ingresses Name>

kubectl apply -f "./vmfile/tg-niren/k8s/pvc-container.yml"
# or `kubectl create -f "path/to/file.yml"`

# 安裝環境文件
kubectl exec -it <Pod Name> sh
curl https://storage.googleapis.com/<Bucket Name>/env.tar.gz -o - | tar -zxv --no-same-owner -C .

kubectl apply -f "./vmfile/tg-niren/k8s/tg-niren.yml"

# 重新啟動服務器
kubectl scale --replicas 0 deployment/tg-niren-deployment
kubectl scale --replicas 1 deployment/tg-niren-deployment
```

