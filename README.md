Telegram Niren
=======


> version： v0.0.0

Use [Telethon](https://github.com/LonamiWebs/Telethon) to operate niren user.



## 使用方式


**安裝環境：**

```
pipenv install

cp -r ./mntfile.example ./mntfile
# edit ./src/env/env.yml
```



### 小工具


```
# 查看命令
pipenv run ./src/tool.py --router
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
pipenv run ./src/tool.py sayHi Ab Cde [...]
```

