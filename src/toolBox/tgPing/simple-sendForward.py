#!/usr/bin/env python3


import pdb
import typing
import os
import re
import asyncio
import utils.novice as novice
import utils.json
from tgkream.tgSimple import telethon, TelegramClient, TgDefaultInit, TgSimple


def run(args: list, _dirpy: str, _dirname: str):
    asyncio.run(asyncRun(args, _dirpy, _dirname))

async def asyncRun(args: list, _dirpy: str, _dirname: str):
    if len(args) < 4:
        raise ValueError('Usage: <phoneNumber> <userIdsJsonFilePath> <forwardLink>')

    phoneNumber = args[1]
    userIdsJsonFilePath = args[2]
    forwardLink = args[3]

    if not os.path.exists(userIdsJsonFilePath):
        raise ValueError('找不到 "{}" 用戶清單文件路徑'.format(userIdsJsonFilePath))
    userPeers = utils.json.load(userIdsJsonFilePath)

    regexForwardLink = r'^https:\/\/t\.me\/([^\/]+)\/(\d+)$'
    matchForwardLink = re.search(regexForwardLink, forwardLink)
    if not matchForwardLink:
        raise ValueError('轉傳來源鏈結 "{}" 不如預期'.format(forwardLink))
    forwardGroup = matchForwardLink.group(1)
    forwardMessageId = int(matchForwardLink.group(2))

    loopTimes = len(userPeers)
    tgTool = TgDefaultInit(TgSimple)

    print('-> 登入用戶')
    client = await tgTool.login(phoneNumber)
    myInfo = await client.get_me()
    print('--> I\'m {} {} ({}) and my phone is +{}.'.format(
        str(myInfo.first_name),
        str(myInfo.last_name),
        str(myInfo.username),
        myInfo.phone,
    ))

    print('-> 多組轉傳')
    async for idx in tgTool.iterLoopInterval(loopTimes, 3):
        readableIdx = idx + 1
        forwardPeer = userPeers[idx]
        print('--> {} {}/{}: {} -> {}'.format(
            novice.dateStringify(novice.dateNow()),
            readableIdx, loopTimes, phoneNumber, forwardPeer
        ))

        sendForwardMethod = 'joinChannel'
        try:
            while True:
                if sendForwardMethod == 'finish' or sendForwardMethod == 'skip':
                    break
                elif sendForwardMethod == 'failed':
                    return
                elif sendForwardMethod == 'joinChannel':
                    print('---> 加入聊天室')
                    try:
                        # inputPeer = await client.get_entity(forwardPeer)
                        # if type(inputPeer) != telethon.types.User:
                        #     print('----> client(functions.channels.JoinChannelRequest)')
                        #     await client(telethon.functions.channels.JoinChannelRequest(
                        #         channel = forwardPeer
                        #     ))
                        print('----> client(functions.channels.JoinChannelRequest)')
                        await client(telethon.functions.channels.JoinChannelRequest(
                            channel = forwardPeer
                        ))
                        sendForwardMethod = 'forwardMessages'
                    except ValueError as err:
                        print('ValueError Error: {} (from: {})'.format(
                            err, 'client(functions.messages.JoinChannelRequest)'
                        ))
                        sendForwardMethod = 'skip'
                    except telethon.errors.FloodWaitError as err:
                        waitTimeSec = err.seconds
                        print('FloodWaitError Error: wait {} seconds. (from: {})'.format(
                            waitTimeSec, 'client(functions.messages.ForwardMessagesRequest)'
                        ))
                        if waitTimeSec < 3600:
                            print('----> FloodWaitError: wait {} seconds.'.format(waitTimeSec))
                            await asyncio.sleep(waitTimeSec + 60)
                        else:
                            sendForwardMethod = 'failed'
                    except Exception as err:
                        errTypeName = err.__class__.__name__
                        isBreak = False
                        errTypeTxt = errTypeName
                        errMsg = ''
                        if errTypeName in _joinChannelKnownErrorTypeInfo:
                            errMsg = _joinChannelKnownErrorTypeInfo[errTypeName]
                        elif errTypeName in _joinChannelInvalidErrorTypeInfo:
                            isBreak = True
                            errMsg = _joinChannelInvalidErrorTypeInfo[errTypeName]
                        else:
                            isBreak = True
                            errTypeTxt = type(err)
                            errMsg = err

                        print('{} Error: {} (from: {})'.format(
                            errTypeTxt, errMsg, 'client(functions.messages.JoinChannelRequest)'
                        ))
                        if isBreak:
                            sendForwardMethod = 'failed'
                        else:
                            sendForwardMethod = 'skip'
                elif sendForwardMethod == 'forwardMessages':
                    print('---> client(functions.messages.ForwardMessagesRequest)')
                    try:
                        await client(telethon.functions.messages.ForwardMessagesRequest(
                            from_peer = forwardGroup,
                            id = [forwardMessageId],
                            to_peer = forwardPeer,
                            random_id = [tgTool.getRandId()]
                        ))
                        sendForwardMethod = 'finish'
                    except ValueError as err:
                        print('ValueError Error: {} (from: {})'.format(
                            err, 'client(functions.messages.JoinChannelRequest)'
                        ))
                        sendForwardMethod = 'skip'
                    except telethon.errors.FloodWaitError as err:
                        waitTimeSec = err.seconds
                        print('FloodWaitError Error: wait {} seconds. (from: {})'.format(
                            waitTimeSec, 'client(functions.messages.ForwardMessagesRequest)'
                        ))
                        if waitTimeSec < 3600:
                            print('----> FloodWaitError: wait {} seconds.'.format(waitTimeSec))
                            await asyncio.sleep(waitTimeSec + 60)
                        else:
                            sendForwardMethod = 'failed'
                    except Exception as err:
                        errTypeName = err.__class__.__name__
                        isBreak = False
                        errTypeTxt = errTypeName
                        errMsg = ''
                        if errTypeName in _sendMessageKnownErrorTypeInfo:
                            errMsg = _sendMessageKnownErrorTypeInfo[errTypeName]
                        elif errTypeName in _sendMessageInvalidErrorTypeInfo:
                            isBreak = True
                            errMsg = _sendMessageInvalidErrorTypeInfo[errTypeName]
                        else:
                            isBreak = True
                            errTypeTxt = type(err)
                            errMsg = err

                        print('{} Error: {} (from: {})'.format(
                            errTypeTxt, errMsg, 'client(functions.messages.ForwardMessagesRequest)'
                        ))
                        if isBreak:
                            sendForwardMethod = 'failed'
                        else:
                            sendForwardMethod = 'skip'
        except Exception as err:
            print('{} Error: {} '.format(type(err), err))
            pdb.set_trace()
            raise err



_joinChannelInvalidErrorTypeInfo = {
    # 程式實作時發現的錯誤
    'PeerFloodError': '限制發送請求 Too many requests。',
}
_joinChannelKnownErrorTypeInfo = {
    'ChannelsTooMuchError': '您加入了太多的頻道/超級群組。',
    'ChannelInvalidError': '無效的頻道對象',
    'ChannelPrivateError': '您尚未加入此頻道/超級群組。另一個原因可能是您被禁止了。',
    # 只在 https://core.telegram.org/method/channels.joinChannel 的錯誤
    # 400 INVITE_HASH_EMPTY
    # 400 INVITE_HASH_EXPIRED
    # 400 INVITE_HASH_INVALID
    # 400 MSG_ID_INVALID
    # 400 PEER_ID_INVALID
    # 400 USERS_TOO_MUCH
    # 400 USER_ALREADY_PARTICIPANT
    # 400 USER_CHANNELS_TOO_MUCH
    # 程式實作時發現的錯誤
    # 'ValueError': 'No user has "{}" as username.', # 沒有此用戶名稱
    'UsernameInvalidError': '沒有人使用此用戶名，或者用戶名不可接受。',
    # NOTE:
    # 發送給 Fortronsmartcontarct 時拋出以下錯誤
    #   telethon.errors.rpcerrorlist.UsernameInvalidError
    #     Nobody is using this username, or the username is unacceptable.
    #     If the latter, it must match r"[a-zA-Z][\w\d]{3,30}[a-zA-Z\d]"
    #     (caused by ResolveUsernameRequest)
    # 對比 ValueError 錯誤的用戶名 infinitron_global
    #   ValueError Error: No user has "infinitron_global" as username
}

_sendMessageInvalidErrorTypeInfo = {
    'MediaEmptyError': '無效的媒體對象，或者當前帳戶可能無法發送它 (例如: 用戶遊戲)。',
    'MessageIdsEmptyError': '沒有提供訊息 ID。',
    'MessageIdInvalidError': '無效的訊息 ID。',
    # 程式實作時發現的錯誤
    'PeerFloodError': '限制發送請求 Too many requests。',
}
_sendMessageKnownErrorTypeInfo = {
    'BroadcastPublicVotersForbiddenError': '您不能在選民公開的地方進行民意測驗。',
    'ChannelInvalidError': '無效的頻道對象。',
    'ChannelPrivateError': '您尚未加入此頻道/超級群組。另一個原因可能是您被禁止了。',
    'ChatAdminRequiredError': '您必須是此聊天的管理員才能執行此操作。',
    'ChatIdInvalidError': '無效的聊天對象 ID。', # ?
    'ChatSendGifsForbiddenError': '您無法在此聊天中發送 GIF。',
    'ChatSendMediaForbiddenError': '您無法在此聊天中發送多媒體。',
    'ChatSendStickersForbiddenError': '您無法在此聊天中發送貼紙。',
    'ChatWriteForbiddenError': '您無法在此聊天中發送訊息。',
    'GroupedMediaInvalidError': 'Invalid grouped media.', # ?
    'InputUserDeactivatedError': '指定的用戶已被刪除。',
    'PeerIdInvalidError': '無效的用戶的 Peer 類型。',
    'RandomIdInvalidError': '無效的隨機識別碼。',
    'UserBannedInChannelError': '您被禁止在超級群組/頻道中發送消息。',
    'UserIsBlockedError': '您已被該用戶封鎖。',
    'UserIsBotError': '機器人無法向其他機器人發送消息。',
    'YouBlockedUserError': '您封鎖了該用戶。',
    # 只在 https://core.telegram.org/method/messages.forwardMessages 的錯誤
    # 400 CHAT_RESTRICTED
    # 403 CHAT_SEND_POLL_FORBIDDEN
    # 400 MSG_ID_INVALID
    # 420 P0NY_FLOODWAIT
    # 420 SLOWMODE_WAIT_X
    # 只在 https://tl.telethon.dev/methods/messages/forward_messages.html 的錯誤
    'PtsChangeEmptyError': 'PTS 不變。', # ?
    'RandomIdDuplicateError': '提供隨機識別碼已經被使用。',
    'ScheduleDateTooLateError': '您嘗試安排的日期距離將來太遠 (已知限制為 1 年零幾個小時)。',
    'ScheduleTooMuchError': '您無法在此聊天中安排更多消息 (最近一次聊天限制為 100 個)。',
    'TimeoutError': '從工作程序中獲取數據時發生超時。',
    # 程式實作時發現的錯誤
    # 'ValueError': 'No user has "{}" as username.', # 沒有此用戶名稱
}

