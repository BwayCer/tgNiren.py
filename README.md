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

