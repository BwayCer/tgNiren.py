Telegram 炸群數量限制
=======


謝謝囉。



## 使用方式


```sh
# 建立容器
./buildVm.sh

docker run -d -p 6379:6379 redislabs/rejson:latest
# 正確路徑在 bwaycer 和 James 的 Telegram 聊天紀錄裡
curl https://storage.googleapis.com/xxx/env.tar.gz -o - | tar -zxv -C .

# 增加群組參與者清單 (會儲存於 "./sendUsers.json")
./runGetParticipants.sh

# 轟炸用戶 (有老闆) (會儲存於 "./logData.json")
# 若要更改圖片請覆蓋 "./the.jpg" 的路徑名
./runSendAdPhoto.sh <訊息內容>
```

**如果看到 "telethon.errors.rpcerrorlist.PeerFloodError: Too many requests" 太多就換一組名單吧。**

