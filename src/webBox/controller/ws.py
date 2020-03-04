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


async def entry() -> None:
    ynCollect = False
    pageId = None
    socket = None
    try:
        while True:
            receiveDatasTxt = await quart.websocket.receive()

            if receiveDatasTxt == 'pin':
                await quart.websocket.send('pon')
                continue

            if receiveDatasTxt == 'register':
                ynCollect = True
                pageId = quart.websocket.cookies.get('pageId')
                socket = quart.websocket._get_current_object()
                serverMix.wsHouse.open(pageId, socket)
                await quart.websocket.send('register-ok')
                continue

            if ynCollect:
                innerSession = serverMix.innerSession.get(pageId)
                if innerSession == None:
                    await quart.websocket.send(json.dumps([{
                        'type': 'ws.close',
                        'message': '頁面識別碼過期。',
                    }]))
                    break

                await _niGraph(pageId, receiveDatasTxt)
                continue
    finally:
        if ynCollect:
            serverMix.wsHouse.close(pageId, socket)


async def _niGraph(pageId: str, receiveDatasTxt: str) -> None:
    try:
        receiveDatas = json.loads(receiveDatasTxt)

        # 相當於請求錯誤
        if type(receiveDatas) != list:
            return

        resultDatas = []
        for item in receiveDatas:
            resultData = {'type': ''}

            try:
                if not 'type' in item:
                    raise KeyError('wschan: 項目缺少必要的 "type" 成員')

                requestMethod = item['type']
                resultData['type'] = requestMethod
                if type(requestMethod) != str:
                    raise TypeError('wschan: 項目 "type" 成員的類型應為字串')

                matchWsMethod = re.search(_regexWsMethod, requestMethod)
                if matchWsMethod == None:
                    raise ValueError('wschan: 項目 "type" 成員表示式格式錯誤')
                fileName = matchWsMethod.group(1)
                methodName = matchWsMethod.group(2)

                if novice.indexOf(_wsChannelList, fileName) == -1:
                    raise KeyError('wschan: 要求的方法文件不存在')

                pyImportPath = _wsChannelDirPyImportPath + '.' + fileName
                # TODO 不知為 `importlib.import_module()` 何會拋出以下訊息
                # Executing <Task pending name='Task-21' coro=<ASGIWebsocketConnection.handle_websocket() running at /home/bwaycer/ys/gitman/crepo/tgNiren.py/.venv/lib/python3.8/site-packages/quart/asgi.py:147> wait_for=<Future pending cb=[<TaskWakeupMethWrapper object at 0x7f72d22eb250>()] created at /usr/lib/python3.8/asyncio/base_events.py:422> cb=[_wait.<locals>._on_completion() at /usr/lib/python3.8/asyncio/tasks.py:507] created at /home/bwaycer/ys/gitman/crepo/tgNiren.py/.venv/lib/python3.8/site-packages/quart/asgi.py:110> took 0.189 seconds
                module = importlib.import_module(pyImportPath)
                if not hasattr(module, methodName):
                    raise KeyError('wschan: 要求的方法不存在')

                action = getattr(importlib.import_module(pyImportPath), methodName)
                if 'prop' in item:
                    result = action(pageId, item['prop'])
                else:
                    result = action(pageId)
                if asyncio.iscoroutine(result):
                    result = await result
                # 測試是否可以編譯為 JSON (若其中包含 Python 的類型則會失敗)
                json.dumps(result)

                for key in result:
                    resultData[key] = result[key]
            except Exception:
                errInfo = novice.sysExceptionInfo()
                resultData['error'] = {
                    'name': errInfo['name'],
                    'message': errInfo['message'],
                }
                novice.logNeedle.push(
                    'Catch error in ws.py\n'
                    '  resultData:\n{}\n'
                    '  errMsg:\n{}'.format(
                        resultData,
                        novice.sysTracebackException()
                    )
                )

            if resultData['type'] != '':
                resultDatas.append(resultData)

        await quart.websocket.send(json.dumps(resultDatas))
    except Exception as err:
        raise err

