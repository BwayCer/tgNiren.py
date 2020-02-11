Telegram Niren
=======


> version： v0.0.0

Use [Telethon](https://github.com/LonamiWebs/Telethon) to operate niren user.



## 使用方式


```
pipenv install
// or
// pip install -r requirements.txt

cp ./src/env.example.yml ./src/env.yml
# edit ./src/env.yml

docker run -d -p 6379:6379 redislabs/rejson:latest

pipenv run ./src/tgNiren.py
```


**小工具：**

```
# 圖片訊息廣告
#   { forwardPeerList: ["someChannelName"[, ...]],   # 轉傳的對象清單
#     url: "./path/to/some.jpg",
#     msg: "文字訊息" }
pipenv run ./src/tool.py adTool.sendAdPhoto "{\"forwardPeerList\":[\"someChannelName\"],\"url\":\"./path/to/some.jpg\",\"msg\":\"文字訊息\"}"

# 塞人入群
pipenv run ./src/tool.py adTool.tuckUserIntoChannel <仿用戶的數量> <用戶來源群> <用戶導入群>
```



## 小工具


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

