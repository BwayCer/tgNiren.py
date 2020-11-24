#!/usr/bin/env python3


import typing
import os
import random
import asyncio
import utils.novice as novice
import webBox.serverMix as serverMix
from tgkream.tgTool import knownError, telethon, TgDefaultInit, TgBaseTool
import webBox.app.utils as appUtils
from webBox.app._wsChannel.niUsersStatus import updateStatus as niUsersStatusUpdateStatus


__all__ = ['getParticipants']


async def getParticipants(pageId: str, wsId: str, prop: typing.Any = None) -> dict:
    if type(prop) != dict:
        return {
            'code': -1,
            'messageType': '_restrictedType',
            'message': _getMessage.logNotRecord(
                _getMessage.baseMsg, '_restrictedType', 'prop', 'Object'
            )
        }
    if not ('groupPeer' in prop and type(prop['groupPeer']) == str):
        return {
            'code': -1,
            'messageType': '_notExpectedType',
            'message': _getMessage.logNotRecord(
                _getMessage.baseMsg, '_notExpectedType', 'prop.groupPeer'
            )
        }
    if not ('offsetDays' in prop and type(prop['offsetDays']) == int):
        return {
            'code': -1,
            'messageType': '_notExpectedType',
            'message': _getMessage.logNotRecord(
                _getMessage.baseMsg, '_notExpectedType', 'prop.offsetDays'
            )
        }

    asyncio.ensure_future(_getParticipantsAction(pageId, prop))
    return {
        'code': 0,
        'message': '請求已接收。'
    }

async def _getParticipantsAction(pageId: str, data: dict):
    niUsersStatusInfo = await appUtils.getNiUsersStatusInfo()
    usableNiUsersCount = niUsersStatusInfo['usableCount']
    if usableNiUsersCount < 1:
        await _getParticipantsAction_send(pageId, {
            'code': -1,
            'messageType': 'Error',
            'message': '工具目前無法使用。',
        })
        return

    groupPeer = data['groupPeer']
    offsetDays = data['offsetDays']

    # 用於打印日誌
    runId = random.randrange(1000000, 9999999)

    novice.logNeedle.push(
        '(runId: {}) {}'.format(runId, 'adTool.getParticipants 初始化...')
    )
    try:
        tgTool = appUtils.getTgTool(1)
        await tgTool.init()
    except Exception as err:
        errTypeName = err.__class__.__name__
        await _getParticipantsAction_send(pageId, {
            'code': -1,
            'messageType': errTypeName,
            'message': _getMessage.catchError(runId, 'init TgTool', {}, errTypeName),
        })
        return

    await niUsersStatusUpdateStatus(usableCount = -1)

    clientInfo = tgTool.pickClient()
    myId = clientInfo['id']
    client = clientInfo['client']

    groupEntity = await client.get_entity(groupPeer)
    print(type(groupEntity), groupEntity.megagroup)
    if type(groupEntity) != telethon.types.Channel or groupEntity.megagroup == False:
        await _getParticipantsAction_send(pageId, {
            'code': -1,
            'messageType': 'Error',
            'message': appUtils.console.logMsg(runId, f'"{groupPeer}" 非群組聊天室。'),
        })
        return

    _, isPrivate = telethon.utils.parse_username(groupPeer)
    if isPrivate:
        appUtils.console.logMsg(runId, f'tgTool.joinGroup() {myId} join {groupPeer}')
        try:
            await tgTool.joinGroup(client, groupPeer)
        except telethon.errors.UserAlreadyParticipantError as err:
            # 已經是聊天的參與者。 (私有聊天室)
            pass
        except Exception as err:
            await tgTool.release()
            await niUsersStatusUpdateStatus(usableCount = 1)

            errTypeName = err.__class__.__name__
            await _getParticipantsAction_send(pageId, {
                'code': -1,
                'messageType': errTypeName,
                'message': _getMessage.catchError(
                    runId,
                    'tgTool.joinGroup()',
                    _joinGroupKnownErrorTypeInfo,
                    errTypeName
                ),
            })
            return

    appUtils.console.logMsg(runId, '_getActiveParticipants()')
    try:
        users = await _getActiveParticipants(client, groupPeer, offsetDays)
        userNames = []
        for user in users:
            username = user.username
            if username == None:
                continue
            userNames.append(username)
    except Exception as err:
        await tgTool.release()
        await niUsersStatusUpdateStatus(usableCount = 1)

        errTypeName = err.__class__.__name__
        payload = {
            'code': -1,
            'messageType': errTypeName,
            'message': '',
        }
        if knownError.has('GetHistoryRequest', err):
            payload.message = appUtils.console.catchErrorMsg(
                runId, 'GetHistoryRequest', knownError.getMsg('GetHistoryRequest', err)
            )
        else:
            payload.message = appUtils.console.catchError(
                runId, '_getActiveParticipants()'
            )

        await _getParticipantsAction_send(pageId, payload)
        return

    await tgTool.release()
    await niUsersStatusUpdateStatus(usableCount = 1)

    await _getParticipantsAction_send(pageId, {
        'code': 1,
        'messageType': 'success',
        'message': _getMessage.log(
            runId, _interactiveMessage, 'success', len(userNames)
        ),
        'participantIds': userNames,
    })


_interactiveMessage = {
    # -1 錯誤
    # 1 成功
    'success': '成功拿到 {} 個用戶名。',
}
_joinGroupKnownErrorTypeInfo = {
    'ChannelsTooMuchError': '您加入了太多的頻道/超級群組。',
    'ChannelInvalidError': '無效的頻道對象。',
    'ChannelPrivateError': '您無法加入私人的頻道/超級群組。另一個原因可能是您被禁止了。',
    'InviteHashEmptyError': '邀請連結丟失。 (私有聊天室)',
    'InviteHashExpiredError': '邀請連結已過期。 (私有聊天室)',
    'InviteHashInvalidError': '無效的邀請連結。 (私有聊天室)',
    'SessionPasswordNeededError': '啟用了兩步驗證，並且需要密碼。 (私有聊天室)(登入錯誤?)',
    'UsersTooMuchError': '超過了最大用戶數 (ex: 創建聊天)。 (私有聊天室)',
    'UserAlreadyParticipantError': '已經是聊天的參與者。 (私有聊天室)',
    # 只有在 https://core.telegram.org/method/messages.importChatInvite 的錯誤
    # 400 MSG_ID_INVALID
    # 400 PEER_ID_INVALID
    # 只有在 https://core.telegram.org/method/channels.JoinChannel 的錯誤
    # 400 INVITE_HASH_EMPTY
    # 400 INVITE_HASH_EXPIRED
    # 400 INVITE_HASH_INVALID
    # 400 MSG_ID_INVALID
    # 400 PEER_ID_INVALID
    # 400 USERS_TOO_MUCH
    # 400 USER_ALREADY_PARTICIPANT
    # 400 USER_CHANNELS_TOO_MUCH
}
# TODO: 之後做多功能提取名單時會有用
_getParticipantsKnownErrorTypeInfo = {
    'ChannelInvalidError': '無效的頻道對象。',
    'ChannelPrivateError': '您無法加入私人的頻道/超級群組。另一個原因可能是您被禁止了。',
    'ChatAdminRequiredError': '您沒有執行此操作的權限。',
    'InputConstructorInvalidError': '提供的構造函數無效。 (*程式錯誤)',
    # 只在 https://tl.telethon.dev/methods/channels/get_participants.html 的錯誤
    'TimeoutError': '從工作程序中獲取數據時發生超時。 (*程式錯誤)',
}

class _getMessage():
    baseMsg = {
        '_undefined': 'Unexpected log message.',
        '_undefinedError': 'Unexpected error message.',
        '_illegalInvocation': 'Illegal invocation.',
        '_notExpectedType': '"{}" is not of the expected type.',
        '_restrictedType': '"{}" must be a `{}` type.',
    }

    def logNotRecord(msgTypeInfos: dict, typeName: str, *args) -> str:
        if typeName in msgTypeInfos:
            msg = msgTypeInfos[typeName]
            if len(args) > 0:
                msg = msg.format(*args)
        else:
            msg = '{} (type: {})'.format(
                _getMessage.baseMsg['_undefined'],
                typeName
            )
        return msg

    def log(runIdCode: str, msgTypeInfos: dict, typeName: str, *args) -> str:
        if typeName in msgTypeInfos:
            msg = msgTypeInfos[typeName]
            if len(args) > 0:
                msg = msg.format(*args)
        else:
            msg = '{} (type: {})'.format(
                _getMessage.baseMsg['_undefined'],
                typeName
            )
        novice.logNeedle.push('(runId: {}) log {}'.format(runIdCode, msg))
        return msg

    def error(runIdCode: str, msgTypeInfos: dict, typeName: str, *args) -> str:
        if typeName in msgTypeInfos:
            msg = msgTypeInfos[typeName]
            if len(args) > 0:
                msg = msg.format(*args)
        else:
            msg = '{} (type: {})'.format(
                _getMessage.baseMsg['_undefinedError'],
                typeName
            )
        novice.logNeedle.push('(runId: {}) error {}'.format(runIdCode, msg))
        return msg

    def catchError(
            runIdCode: str,
            fromState: str,
            errorTypeInfos: dict,
            typeName: str) -> str:
        errMsg = errorTypeInfos[typeName] \
            if typeName in errorTypeInfos \
            else novice.sysTracebackException()
        novice.logNeedle.push(
            '(runId: {}) from {} Failed {}'.format(runIdCode, fromState, errMsg)
        )
        return errMsg

async def _getParticipantsAction_send(
        pageId: str,
        payload: dict) -> None:
    await serverMix.wsHouse.send(pageId, fnResult = {
        'name': 'adTool.getParticipantsAction',
        'result': payload,
    })

async def _getActiveParticipants(
        client: telethon.TelegramClient,
        groupPeer: str,
        offsetDays: float = 1,
        amount: int = 0) -> typing.List[telethon.types.User]:
    if offsetDays < 1:
        raise Exception('時間偏移量須為大於 1 的正數。')
    if amount < 0:
        raise Exception('取得用戶總量須為正整數。')

    theDt = novice.dateUtcNowOffset(days = -1 * offsetDays)

    # NOTE: 關於 `GetHistoryRequest()` 方法
    # https://core.telegram.org/method/messages.getHistory
    # https://tl.telethon.dev/methods/messages/get_history.html
    # 1. 當對象為用戶時，沒有訊息?! (2020.11.23 紀錄)
    # 關於參數值：
    #   1. `offset_id`, `add_offset` 用於選取在特定訊息前或後的訊息，不使用則傳入 `0`。
    #   2. `offset_date`, `max_id`, `min_id` 用於選取在特定範圍內的訊息
    #      注意！ 感覺是先使用 `offset_date` 和 `limit` 先選定範圍，
    #      再篩選符合的 `max_id`, `min_id` 的項目，
    #      所以當 `offset_date` 不變的情況下，取得訊息的數量只會越來越少。
    #   3. `offset_date` 若傳入 `0|None`，則預設為當前時間。
    #   4. Telegram 時間為 UTC 時間。
    # 關於回傳值：
    #   https://core.telegram.org/constructor/messages.channelMessages
    #   1. `count` 為該聊天室紀錄於服務端的總訊息比數。
    #      (但可能不完全紀錄於服務端 ?! (官方說的))
    #   2. 回傳的訊息是依時間倒序排序的。
    #   3. `chats`, `users` 中包含 `messages` 所提到的對象 (ex: 轉傳的訊息對象也在裡面)
    #   4. `limit` 最多為 100 則。 (2020.11.23 紀錄)

    result = await client(telethon.functions.messages.GetHistoryRequest(
        peer = groupPeer,
        offset_id = 0,
        offset_date = theDt,
        add_offset = 0,
        limit = 1,
        max_id = 0,
        min_id = 0,
        hash = 0
    ))
    oldMsgId = result.messages[0].id if len(result.messages) > 0 else 1

    isBleak = False
    currDate = None
    currMinMsgId = 0
    userList = []
    activeUserList = []
    while True:
        result = await client(telethon.functions.messages.GetHistoryRequest(
            peer = groupPeer,
            offset_id = 0,
            offset_date = currDate,
            add_offset = 0,
            limit = 100,
            max_id = currMinMsgId,
            min_id = oldMsgId,
            hash = 0
        ))
        print(f'pts: {result.pts}, count: {result.count}, messages: {len(result.messages)}, chats: {len(result.chats)}, users: {len(result.users)}')

        messagesLength = len(result.messages)
        if messagesLength == 0:
            break
        print(f'  {result.messages[0].id}({result.messages[0].date}) ~ {result.messages[messagesLength - 1].id}({result.messages[messagesLength - 1].date})')

        for user in result.users:
            # 排除 自己, 已刪除帳號, 機器人
            if user.is_self or user.deleted or user.bot:
                continue

            # 過濾已抓取的
            if user.id in userList:
                continue

            userList.append(user.id)
            activeUserList.append(user)

            if amount != 0 and len(activeUserList) >= amount:
                isBleak = True
                break
        print(f'  get {len(result.users)} users -> {len(activeUserList)}')

        if isBleak:
            break

        currDate = result.messages[messagesLength - 1].date
        currMinMsgId = result.messages[messagesLength - 1].id

    return activeUserList

