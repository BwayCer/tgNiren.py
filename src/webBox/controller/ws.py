#!/usr/bin/env python3


import os
import json
import re
import asyncio
import importlib
import quart
import utils.novice as novice
import webBox.serverMix as serverMix


__all__ = ['init', 'entry']


_wsChannelDirPyImportPath = ''
_wsChannelList = []
_regexWsMethod = r'^(.*)\.([^.]*)$'


def init(wsChannelDirPath: str) -> None:
    global _wsChannelDirPyImportPath, _wsChannelList
    _wsChannelDirPyImportPath = wsChannelDirPath.replace('/', '.')
    _wsChannelList = os.listdir(novice.py_dirname + '/' + wsChannelDirPath)

    regexClearExt = r'\.py$'
    for idx in range(len(_wsChannelList)):
        _wsChannelList[idx] = re.sub(regexClearExt, '', _wsChannelList[idx])

    _wsExpiredCheckLoop()


async def entry() -> None:
    currTask = asyncio.current_task()
    connectState = 'await' # await -> handshake -> connect

    @novice.dSetTimeout(intervalSec = 7, loop = 1)
    def expiredCheck():
        if not currTask.done() and connectState != 'connect':
            currTask.cancel()

    pageId = None
    wsId = None
    try:
        while True:
            receiveDataTxt = await quart.websocket.receive()

            if receiveDataTxt == 'pin':
                if connectState == 'connect':
                    novice.logNeedle.push(f'store {pageId}:{wsId} pinpon 延長時間')
                    serverMix.innerSession.extendedDuration(pageId)
                    serverMix.wsHouse.channelExtendedDuration(wsId)
                await quart.websocket.send('pon')
                continue

            if receiveDataTxt == 'handshake':
                if connectState == 'await':
                    rtnInfo = _addWsProxy(quart.websocket, currTask)
                    if rtnInfo['stateCode'] != 200:
                        # 握手失敗
                        await quart.websocket.send(
                            f'{{"stateCode": {rtnInfo["stateCode"]}}}'
                        )
                        break
                    connectState = 'handshake'
                    pageId = rtnInfo['pageId']
                    wsId = rtnInfo['wsId']
                    novice.logNeedle.push(f'ws.entry: {pageId}:{wsId} handshake.')
                    rtnInfo = None
                await serverMix.wsHouse.send(wsId, stateCode = 401)
                continue

            if connectState == 'handshake':
                try:
                    receiveData = json.loads(receiveDataTxt)
                except Exception as err:
                    break

                if type(receiveData) != dict:
                    break
                if not 'wsId' in receiveData or receiveData['wsId'] != wsId:
                    break

                connectState = 'connect'
                await serverMix.wsHouse.send(wsId, stateCode = 200)
                continue

            if connectState == 'connect':
                try:
                    receiveData = json.loads(receiveDataTxt)
                    if type(receiveData) != dict or receiveData['wsId'] != wsId:
                        return
                except Exception as err:
                    # 請求頭資訊錯誤
                    await serverMix.wsHouse.send(wsId, stateCode = 404)

                novice.logNeedle.push(f'store {pageId}:{wsId} ws receive 延長時間')
                serverMix.innerSession.extendedDuration(pageId)
                serverMix.wsHouse.channelExtendedDuration(wsId)
                await _niGraph(pageId, wsId, receiveData)
                continue

            # TODO: 將非法請求寫入日誌
            novice.logNeedle.push(f'ws.entry: 非法請求: {receiveDataTxt}')
    # except asyncio.CancelledError:
        # wsProxy cancel.
    finally:
        if connectState != 'await':
            novice.logNeedle.push(f'ws.entry: {pageId}:{wsId} server close connect.')
            _removeWsProxy(pageId, wsId)


def _addWsProxy(wsProxy: quart.local.LocalProxy, task: asyncio.Task) -> dict:
    pageId = wsProxy.cookies.get('pageId')
    innerSession = serverMix.innerSession.get(pageId)
    if innerSession == None:
        return {'stateCode': 404}

    # NOTE:
    # 若使用 `quart.websocket (type: quart.local.LocalProxy)`
    # 物件做通訊 (`send()`) 會遇到上下文不同 (好像是 task 不同的關係) 而失敗。
    # 但若使用
    # `quart.websocket._get_current_object() (type: quart.wrappers.request.Websocket)`
    # 則不受影響。
    socket = quart.websocket._get_current_object()
    wsId = serverMix.wsHouse.addChannel(task, pageId, socket)

    if not 'wsData' in innerSession:
        innerSession['wsData'] = novice.CacheData()
    innerSession['wsData'].register(key = wsId)

    return {'stateCode': 200, 'pageId': pageId, 'wsId': wsId}

def _removeWsProxy(pageId: str, wsId: str):
    innerSession = serverMix.innerSession.get(pageId)
    if innerSession != None:
        innerSession['wsData'].remove(wsId)
    serverMix.wsHouse.removeChannel(wsId)

# NOTE:
# 為保持 websocket 存在時，session 必須存在的條件，
# 假設 session 與 websocket 的過期檢查迴圈是正常的狀態下，
# 只要遵守以下設定，那麼即使沒有監聽 session 的過期事件也無妨。
#   1. session 延長時間 >> websocket 過期檢查時間 >= websocket 延長時間
#   2. 當 websocket 持續時間被延長的同時也必須延長 session 的持續時間。
# 安全起見，將 session 延長時間設為 websocket 過期檢查時間與 websocket 延長時間的三倍。
def _wsExpiredCheckLoop():
    @novice.dSetTimeout(intervalSec = 3600 * 2 * 0.01)
    async def expiredCheck():
        channelCache = serverMix.wsHouse.channelCache
        if channelCache.size() == 0:
            return

        channelCacheData = channelCache.data
        nowTimeMs = novice.dateUtcNowTimestamp()
        for wsId in list(channelCacheData):
            itemData = channelCacheData[wsId]
            task = itemData['task']

            innerSession = serverMix.innerSession.get(itemData['pageId'])
            if innerSession == None:
                # TODO: 觀察是否還會發生，如果不會就刪除吧！
                # 頁面識別碼過期
                novice.logNeedle.push('store 頁面識別碼過期')
                await serverMix.wsHouse.send(wsId, stateCode = 404)
                task.cancel()
                continue

            if itemData['expiryTimestamp'] <= nowTimeMs:
                # 連線閒置過久
                novice.logNeedle.push(f'store {wsId} 連線閒置過久')
                await serverMix.wsHouse.send(wsId, stateCode = 404)
                task.cancel()
                continue

            novice.logNeedle.push(f'store {wsId} 在線')

async def _niGraph(pageId: str, wsId: str, receiveData: dict) -> None:
    try:
        # 沒有請求的請求
        if not 'fns' in receiveData:
            return

        rtnDatas = []
        for item in receiveData['fns']:
            if not 'randId' in item or type(item['randId']) != int:
                continue

            rtnData = {'randId': item['randId']}

            try:
                if not 'name' in item:
                    raise KeyError('wschan: 項目缺少必要的 "name" 成員')

                requestMethod = item['name']
                rtnData['name'] = requestMethod
                if type(requestMethod) != str:
                    raise TypeError('wschan: 項目 "name" 成員的類型應為字串')

                matchWsMethod = re.search(_regexWsMethod, requestMethod)
                if matchWsMethod == None:
                    raise ValueError('wschan: 項目 "name" 成員表示式格式錯誤')
                fileName = matchWsMethod.group(1)
                methodName = matchWsMethod.group(2)

                if novice.indexOf(_wsChannelList, fileName) == -1:
                    raise KeyError('wschan: 要求的方法文件不存在')

                pyImportPath = _wsChannelDirPyImportPath + '.' + fileName
                # TODO 不知為 `importlib.import_module()` 何會拋出以下訊息
                # Executing
                #   <Task pending name='Task-21'
                #     coro=<ASGIWebsocketConnection.handle_websocket() running at /home/bwaycer/ys/gitman/crepo/tgNiren.py/.venv/lib/python3.8/site-packages/quart/asgi.py:147>
                #     wait_for=<Future pending
                #                cb=[<TaskWakeupMethWrapper object at 0x7f72d22eb250>()]
                #                created at /usr/lib/python3.8/asyncio/base_events.py:422>
                #     cb=[_wait.<locals>._on_completion() at /usr/lib/python3.8/asyncio/tasks.py:507]
                #     created at /home/bwaycer/ys/gitman/crepo/tgNiren.py/.venv/lib/python3.8/site-packages/quart/asgi.py:110>
                # took 0.189 seconds
                module = importlib.import_module(pyImportPath)
                if not hasattr(module, methodName):
                    raise KeyError('wschan: 要求的方法不存在')

                action = getattr(importlib.import_module(pyImportPath), methodName)
                if 'prop' in item:
                    result = action(pageId, wsId, item['prop'])
                else:
                    result = action(pageId, wsId)
                if asyncio.iscoroutine(result):
                    result = await result
                # 測試是否可以編譯為 JSON (若其中包含 Python 的類型則會失敗)
                json.dumps(result)

                rtnData['result'] = result
            except Exception:
                errInfo = novice.sysExceptionInfo()
                rtnData['error'] = {
                    'name': errInfo['name'],
                    'message': errInfo['message'],
                    'stack': errInfo['stackList'],
                }
                novice.logNeedle.push(
                    'Catch error in ws.py\n'
                    '  rtnData:\n{}\n'
                    '  errMsg:\n{}'.format(
                        rtnData,
                        novice.sysTracebackException()
                    )
                )

            rtnDatas.append(rtnData)

        await serverMix.wsHouse.send(wsId, rtns = rtnDatas)
    except Exception as err:
        print('from {} Failed {}: {}\nreceiveData: {}'.format(
            'ws._niGraph', type(err), err, receiveData
        ))

