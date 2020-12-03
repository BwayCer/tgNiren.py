辛蒂的帳戶
=======


辛蒂 (Cindy) 是一位在 Telegram 上販賣虛擬號的人物，
此工具是透過其給予的資料來執行自動化帳號創建。

關於虛擬號的使用受到 Telegram 官方的嚴格限制，
非常容易被官方封鎖，
除非是少量且自用的情況，
否則筆者不建議購買此類帳號。



## 使用方式


```
# 把辛蒂提供的資料轉 JSON
pipenv run ./src/tool.py modemPool.cindy txtToJson ./example/cindy/modemCardTable.txt
cat ./example/cindy/modemCardTable.txt.json

# 自動註冊 Telegram 並加入指定群組
pipenv run ./src/tool.py modemPool.cindy autoLogin \
    ./example/cindy/modemCardTable.txt.json <TG 群組識別碼> <仿用戶中間名>
```

