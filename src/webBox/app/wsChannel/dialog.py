#!/usr/bin/env python3


import typing
import os
import random
import datetime
import asyncio
import utils.novice as novice
import webBox.serverMix as serverMix
import webBox.app.utils as appUtils
from tgkream.tgTool import knownError, telethon, TgDefaultInit, TgBaseTool


__all__ = ['allRespond', 'sendMessage']


_getRespondDialog_task = None
_updateIntervalTimedelta = datetime.timedelta(seconds = 10 * 3)
_prevTimestamp = novice.dateUtcNow() - _updateIntervalTimedelta
_tgAppMain = novice.py_env['tgApp']['main']
_listenWsId = []
_prevRespondDialogInfo = {
    'timestamp': 0,
    'totalNiUserCount': 0,
    'currentNiUserCount': 0,
    'dialogs': [],
}


async def allRespond(pageId: str, wsId: str, prop: typing.Any = None) -> dict:
    runId = random.randrange(1000000, 9999999)

    global _getRespondDialog_task
    task = _getRespondDialog_task

    dtUtcNow = novice.dateUtcNow()
    timedelta = dtUtcNow - _prevTimestamp
    if timedelta < _updateIntervalTimedelta:
        return {
            'code': 2,
            'messageType': 'record',
            'message': appUtils.console.log(
                runId, _allRespondMessage, 'record'
            ),
            'respondDialogInfo': _prevRespondDialogInfo,
        }

    if not wsId in _listenWsId:
        _listenWsId.append(wsId)

    if task == None or task.done():
        task = _getRespondDialog_task \
            = asyncio.create_task(_allRespondAction(runId))
        _prevRespondDialogInfo['dialogs'].clear()
        return {
            'code': 0,
            'messageType': 'requestReceived',
            'message': appUtils.console.log(
                runId, _allRespondMessage, 'requestReceived'
            ),
        }
    else:
        respondDialogInfo = _prevRespondDialogInfo.copy()
        respondDialogInfo['addDialogs'] = _prevRespondDialogInfo['dialogs']
        del respondDialogInfo['dialogs']
        return {
            'code': 1,
            'messageType': 'executing',
            'message': appUtils.console.log(
                runId, _allRespondMessage, 'executing'
            ),
            'respondDialogInfo': respondDialogInfo,
        }

async def _allRespondAction(runId: str) -> dict:
    global _prevTimestamp
    global _prevRespondDialogInfo

    logName = 'allRespondAction'
    isCreatedTgTool = False
    latestStatus = '初始化...'
    try:
        tgTool = TgDefaultInit(
            TgBaseTool,
            clientCount = 0,
            papaPhone = novice.py_env['papaPhoneNumber']
        )
        isCreatedTgTool = True

        chanDataNiUsers = tgTool.chanDataNiUsers
        usablePhones = chanDataNiUsers.getUsablePhones()
        niUsers = chanDataNiUsers.chanData.data['niUsers']
        bandPhones = niUsers['bandList']
        lockPhones = niUsers['lockList']
        niUsers = None
        allCount = len(usablePhones)

        clientCount = 0
        for idx in range(allCount):
            phoneNumber = usablePhones[idx]
            if phoneNumber in bandPhones or phoneNumber in lockPhones:
                continue
            client = await tgTool.login(phoneNumber)
            if client != None:
                clientCount += 1
        tgTool.clientCount = clientCount

        if clientCount == 0:
            await _asyncLogSend(_listenWsId, logName, {
                'code': 2,
                'messageType': 'noNiUser',
                'message': appUtils.console.log(
                    runId, _allRespondMessage, 'noNiUser'
                ),
            })
            return

        _prevRespondDialogInfo['totalNiUserCount'] = allCount
        _prevRespondDialogInfo['currentNiUserCount'] = clientCount
        respondDialogInfo = {
            'timestamp': 0,
            'totalNiUserCount': allCount,
            'currentNiUserCount': clientCount,
            'addDialogs': [],
        }

        readableIdx = 0
        async for clientInfo in tgTool.iterPickClient(1, 1):
            readableIdx = readableIdx + 1
            myId = clientInfo['id']
            client = clientInfo['client']

            latestStatus = f'{readableIdx}/{clientCount} 讀取 +{myId} 對話'
            await _asyncLogSend(_listenWsId, logName, {
                'code': 1,
                'messageType': 'log',
                'message': appUtils.console.logMsg(runId, latestStatus),
            })
            try:
                dialogs = await client(telethon.functions.messages.GetDialogsRequest(
                    offset_date = None,
                    offset_id = 0,
                    offset_peer = telethon.types.InputPeerEmpty(),
                    limit = 100,
                    hash = 0
                ))
            except Exception as err:
                if knownError.has('GetDialogsRequest', err):
                    errTypeName = err.__class__.__name__
                    errMsg = knownError.getMsg('GetDialogsRequest', err)
                else:
                    errTypeName = type(err)
                    errMsg = err

                await _asyncLogSend(_listenWsId, logName, {
                    'code': 1,
                    'messageType': 'error',
                    'message': appUtils.console.catchErrorMsg(
                        runId, 'client(messages.GetDialogsRequest)',
                        f'+{myId} get {errTypeName} Error: {errMsg}'
                    ),
                })
                continue

            if type(dialogs) == telethon.types.messages.DialogsNotModified:
                continue

            addDialogInfos = []
            for message in dialogs.messages:
                if type(message) != telethon.types.Message:
                    continue

                dialogInfo = await _getDialogInfo(
                    tgTool, message, dialogs.chats, dialogs.users
                )
                if dialogInfo == None:
                    continue

                dialogInfo['myId'] = myId
                addDialogInfos.append(dialogInfo)


            dtUtcNow = novice.dateUtcNow()
            dtUtcNowTimestamp = novice.dateUtcTimestamp(dtUtcNow)
            dialogInfos = _prevRespondDialogInfo['dialogs']

            _prevRespondDialogInfo['timestamp'] = dtUtcNowTimestamp
            dialogInfos.extend(addDialogInfos)
            dialogInfos.sort(key = lambda item: item['timestamp'], reverse = True)

            respondDialogInfo['timestamp'] = dtUtcNowTimestamp
            respondDialogInfo['addDialogs'] = addDialogInfos

            await _asyncLogSend(_listenWsId, logName, {
                'code': 1,
                'messageType': 'addNew',
                'message': appUtils.console.log(
                    runId, _allRespondMessage, 'addNew', myId
                ),
                'respondDialogInfo': respondDialogInfo,
            })

        _prevTimestamp = dtUtcNow
        await _asyncLogSend(_listenWsId, logName, {
            'code': 2,
            'messageType': 'complete',
            'message': appUtils.console.log(
                runId, _allRespondMessage, 'complete'
            ),
            'respondDialogInfo': _prevRespondDialogInfo,
        })
    except Exception as err:
        errMsg = novice.sysTracebackException()
        latestStatus += ' (失敗)' + '\n' + errMsg
        await _asyncLogSend(_listenWsId, logName, {
            'code': -1,
            'messageType': 'error',
            'message': appUtils.console.errorMsg(runId, latestStatus),
        })
    finally:
        _listenWsId.clear()
        if isCreatedTgTool:
            await tgTool.release()
        appUtils.console.logMsg(runId, '讀取對話狀態回復。')

async def sendMessage(pageId: str, wsId: str, prop: typing.Any = None) -> dict:
    if type(prop) != dict:
        return {
            'code': -1,
            'message': '"prop" 參數必須是 `Object` 類型。',
        }
    if not ('niUsersId' in prop and type(prop['niUsersId']) == str):
        return {
            'code': -1,
            'message': '"prop.niUsersId" 參數不符合預期',
        }
    if not ('targetId' in prop and type(prop['targetId']) == str):
        return {
            'code': -1,
            'message': '"prop.targetId" 參數不符合預期',
        }
    if not ('targetAccessHash' in prop and type(prop['targetAccessHash']) == str):
        return {
            'code': -1,
            'message': '"prop.targetAccessHash" 參數不符合預期',
        }
    if not ('message' in prop and type(prop['message']) == str):
        return {
            'code': -1,
            'message': '"prop.message" 參數不符合預期',
        }

    runId = random.randrange(1000000, 9999999)

    global _getRespondDialog_task
    task = _getRespondDialog_task

    if task == None or not task.done():
        return {
            'code': -1,
            'messageType': 'notReadDialog',
            'message': appUtils.console.log(
                runId, _sendMessageMessage, 'notReadDialog'
            ),
        }

    dialogInfo = None
    for info in _prevRespondDialogInfo['dialogs']:
        if prop['niUsersId'] == info['myId'] \
                and prop['targetId'] == info['entityId'] \
                and prop['targetAccessHash'] == info['entityAccessHash']:
            dialogInfo = info
            break
    if dialogInfo == None:
        return {
            'code': -1,
            'messageType': 'notFindDialog',
            'message': appUtils.console.log(
                runId, _sendMessageMessage, 'notFindDialog'
            ),
        }

    targetTypeName = dialogInfo['entityTypeName']
    if targetTypeName != 'Chat' \
            and targetTypeName != 'User' \
            and targetTypeName != 'Channel':
        return {
            'code': -1,
            'messageType': 'notFindDialog',
            'message': appUtils.console.log(
                runId, _sendMessageMessage, 'entityTypeInvalid', targetTypeName
            ),
        }

    asyncio.ensure_future(_sendMessageAction(runId, wsId, {
        'niUsersId': prop['niUsersId'],
        'targetId': prop['targetId'],
        'targetAccessHash': prop['targetAccessHash'],
        'targetTypeName': targetTypeName,
        'targetName': dialogInfo['chatName'],
        'message': prop['message'],
    }))
    return {
        'code': 0,
        'messageType': 'requestReceived',
        'message': appUtils.console.log(
            runId, _sendMessageMessage, 'requestReceived'
        ),
    }

async def _sendMessageAction(runId: str, wsId: str, data: dict):
    logName = 'sendMessageAction'
    latestStatus = '初始化...'
    isCreatedTgTool = False
    try:
        niUsersId = data['niUsersId']
        targetId = int(data['targetId'])
        targetAccessHash = int(data['targetAccessHash'])
        targetTypeName = data['targetTypeName']
        targetName = data['targetName']
        message = data['message']

        tgTool = TgDefaultInit(
            TgBaseTool,
            clientCount = 1,
            papaPhone = novice.py_env['papaPhoneNumber']
        )
        isCreatedTgTool = True
        client = await tgTool.login(niUsersId)
        if client == None:
            await _asyncLogSend(wsId, logName, {
                'code': -1,
                'messageType': 'niUserIsBusy',
                'message': appUtils.console.log(
                    runId, _sendMessageMessage, 'niUserIsBusy'
                ),
            })
            return

        targetPeer = ''
        if targetTypeName == 'Chat':
            targetPeer = telethon.types.InputPeerChat(
                chat_id = targetId
            )
        elif targetTypeName == 'User':
            targetPeer = telethon.types.InputPeerUser(
                user_id = targetId,
                access_hash = targetAccessHash
            )
        elif targetTypeName == 'Channel':
            telethon.types.InputPeerChannel(
                channel_id = targetId,
                access_hash = targetAccessHash
            )

        latestStatus = appUtils.console.log(
            runId, _sendMessageMessage, 'sendMessage', niUsersId, targetName, ''
        )
        await _asyncLogSend(wsId, logName, {
            'code': 1,
            'messageType': 'sendMessage',
            'message': latestStatus,
        })
        try:
            print(targetPeer)
            await client(telethon.functions.messages.SendMessageRequest(
                peer = targetPeer,
                message = message,
                random_id = tgTool.getRandId()
            ))
            await _asyncLogSend(wsId, logName, {
                'code': 2,
                'messageType': 'sendMessage',
                'message': appUtils.console.log(
                    runId, _sendMessageMessage, 'sendMessage',
                    niUsersId, targetName, ' ok'
                ),
            })
        except Exception as err:
            if knownError.has('SendMessageRequest', err):
                errTypeName = err.__class__.__name__
                errMsg = knownError.getMsg('SendMessageRequest', err)
            else:
                errTypeName = type(err)
                errMsg = err

            await _asyncLogSend(wsId, logName, {
                'code': -1,
                'messageType': 'sendMessageError',
                'message': appUtils.console.catchError(
                    runId, 'client(messages.SendMessageRequest)',
                    _sendMessageMessage, 'sendMessageError',
                    niUsersId, targetName, errTypeName, errMsg
                ),
            })
    except Exception as err:
        errMsg = novice.sysTracebackException()
        latestStatus += ' (失敗)' + '\n' + errMsg
        await _asyncLogSend(wsId, logName, {
            'code': -1,
            'messageType': 'error',
            'message': appUtils.console.errorMsg(runId, latestStatus),
        })
    finally:
        if isCreatedTgTool:
            await tgTool.release()
        appUtils.console.logMsg(runId, '傳送訊息狀態回復。')


_allRespondMessage = {
    # -1 程式錯誤
    # 0 請求已接收
    'requestReceived': '請求已接收。',
    # 1 程序執行中
    'executing': '讀取部分紀錄，並持續等待結果。',
    'addNew': '完成讀取 +{} 對話。',
    # 2 完成
    'noNiUser': '沒有可用的仿用戶或仿用戶忙線中。',
    'complete': '全部讀取完成。',
    'record': '讀取過往紀錄。',
}

_sendMessageMessage = {
    # -1 程式錯誤
    'notReadDialog': '請先讀取對話或等待對話完全讀取完成。',
    'notFindDialog': '對話已過期，請嘗試重新整理。',
    'entityTypeInvalid': '對話對象類型無效。 ({})',
    'niUserIsBusy': '仿用戶忙碌中，請稍後再嘗試。',
    'sendMessageError': '傳送訊息： {} -> {} get {} Error: {}',
    # 0 請求已接收
    'requestReceived': '請求已接收。',
    # 1 & 2
    'sendMessage': '傳送訊息： {} -> {}{}',
}

async def _getDialogInfo(
        tgTool: TgBaseTool,
        message: telethon.types.Message,
        chats: list,
        users: list) -> typing.Union[None, dict]:
    if message.out:
        return None

    peerEntity = _findPeer(message.peer_id, chats, users)
    if peerEntity == None:
        return None

    peerInfo = await tgTool.parsePeer(peerEntity)

    if peerInfo['isBot'] or peerInfo['isChannel']:
        return None

    if message.from_id == None:
        fromPeerInfo = {
            'chatTypeName': None,
            'name': None,
        }
    else:
        fromPeerEntity = _findPeer(message.from_id, chats, users)
        if peerEntity == None:
            return None

        fromPeerInfo = await tgTool.parsePeer(fromPeerEntity)

        if fromPeerInfo['isBot']:
            return None

    return {
        'entityId': str(peerInfo['id']),
        # 超過 JS 處理數字的極限
        'entityAccessHash': str(peerInfo['accessHash']),
        'entityTypeName': peerInfo['entityTypeName'],
        'chatTypeName': peerInfo['chatTypeName'],
        'chatName': peerInfo['name'],
        'fromTypeName': fromPeerInfo['chatTypeName'],
        'fromName': fromPeerInfo['name'],
        'timestamp': novice.dateUtcTimestamp(message.date),
        'message':
            ('(有媒體訊息) ' if message.media != None else '')
            + message.message
        ,
    }

def _findPeer(
        peer: typing.Union[
            telethon.types.PeerChannel,
            telethon.types.PeerChat,
            telethon.types.PeerUser,
        ],
        chats: list,
        users: list) -> typing.Union[
            None,
            telethon.types.Chat,
            telethon.types.User,
            telethon.types.Channel,
        ]:
    peerType = type(peer)
    chatList = ''
    chatId = 0
    if peerType == telethon.types.PeerChannel:
        chatList = chats
        chatId = peer.channel_id
    elif peerType == telethon.types.PeerChat:
        chatList = chats
        chatId = peer.chat_id
    elif peerType == telethon.types.PeerUser:
        chatList = users
        chatId = peer.user_id

    for chat in chatList:
        chatType = type(chat)
        if chatType == telethon.types.Chat \
                or chatType == telethon.types.Channel \
                or chatType == telethon.types.User:
            if chat.id == chatId:
                return chat

    return None

async def _asyncLogSend(pageId: str, name: str, result: typing.Any):
    await serverMix.wsHouse.send(pageId, fnResult = {
        'name': f'dialog.{name}',
        'result': result,
    })

