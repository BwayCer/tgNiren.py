#!/usr/bin/env python3


import typing
import random
import asyncio
import utils.novice as novice
from tgkream.tgTool import telethon, TgDefaultInit, TgBaseTool


def run(args: list, _dirpy: str, _dirname: str):
    asyncio.run(asyncRun(args, _dirpy, _dirname))


async def asyncRun(args: list, _dirpy: str, _dirname: str):
    userSourceGroup = args[1]
    forwardLinkGroup = args[2]
    forwardLinkId = int(args[3])
    usedClientCount = int(args[4])
    offsetDays = float(args[5])

    niUserChannlePeer = novice.py_env['peers']['niUserChannle']

    # 用於打印日誌
    runId = random.randrange(1000000, 9999999)
    latestStatus = ''
    try:
        latestStatus = '炸群進度： 初始化...'
        novice.logNeedle.push(f'(runId: {runId}) {latestStatus}')
        tgTool = TgDefaultInit(
            TgBaseTool,
            clientCount = usedClientCount,
            papaPhone = novice.py_env['papaPhoneNumber']
        )
        await tgTool.init()
    except Exception as err:
        latestStatus += ' (失敗)'
        novice.logNeedle.push(f'(runId: {runId}) {latestStatus}')
        raise err

    try:
        latestStatus = '炸群進度： 取得前置資料...'
        novice.logNeedle.push(f'(runId: {runId}) {latestStatus}')

        # NOTE: 當私有聊天室轉公開聊天室後，舊的私有連結仍可用
        _, isPrivate = telethon.utils.parse_username(userSourceGroup)
        if isPrivate:
            novice.logNeedle.push(f'(runId: {runId}) 請提供公開群組')
            return
        peerInfo = await tgTool.parsePeer(userSourceGroup)
        if peerInfo['isGroup'] == False:
            novice.logNeedle.push(f'(runId: {runId}) 請提供公開群組')
            return

        async with tgTool.usePapaClient() as client:
            speakUsers = await tgTool.getSpeakers(
                client = client,
                groupPeer = userSourceGroup,
                offsetDays = offsetDays,
                amount = usedClientCount * 50
            )
            mentionUserMsgIds = await _mentionUsers(
                client = client,
                groupPeer = niUserChannlePeer,
                users = speakUsers,
                separation = ', '
            )
    except Exception as err:
        await tgTool.release()

        latestStatus += ' (失敗)'
        novice.logNeedle.push(f'(runId: {runId}) {latestStatus}')
        raise err

    takeUserListLength = -1
    try:
        latestStatus = '炸群進度： 同步資料...'
        novice.logNeedle.push(f'(runId: {runId}) {latestStatus}')

        tgClientTaskInfo = {}
        async for clientInfo in tgTool.iterPickClient(1):
            myId = clientInfo['id']
            client = clientInfo['client']

            # 仿用戶對自己所執行的目標用戶至少需查詢一次
            targetUsers = await _getTargetUsers(
                tgTool = tgTool,
                client = client,
                groupPeer = niUserChannlePeer,
                msgIds = mentionUserMsgIds
            )
            targetUsersLength = len(targetUsers)
            if takeUserListLength == -1 or targetUsersLength < takeUserListLength:
                takeUserListLength = targetUsersLength

            tgClientTaskInfo[myId] = {
                'targetUsers': targetUsers,
            }
    except Exception as err:
        await tgTool.release()

        latestStatus += ' (失敗)'
        novice.logNeedle.push(f'(runId: {runId}) {latestStatus}')
        raise err

    try:
        bandNiUserList = []
        idx = 0
        async for clientInfo in tgTool.iterPickClient(-1, 1):
            readableIdx = idx + 1
            myId = clientInfo['id']
            client = clientInfo['client']

            if myId in bandNiUserList:
                if len(bandNiUserList) == usedClientCount:
                    break
                continue

            try:
                forwardUser = tgClientTaskInfo[myId]['targetUsers'][idx]
                peerInfo = await tgTool.parsePeer(forwardUser)

                latestStatus = '炸群進度： {}/{} 由 {} 寄送給 {}'.format(
                    readableIdx, takeUserListLength, myId, peerInfo['name']
                )
                novice.logNeedle.push(f'(runId: {runId}) {latestStatus}')

                inputEntity = telethon.types.InputPeerUser(
                    user_id = forwardUser.id,
                    access_hash = forwardUser.access_hash
                )
                await client(telethon.functions.messages.ForwardMessagesRequest(
                    from_peer = forwardLinkGroup,
                    id = [forwardLinkId],
                    to_peer = inputEntity,
                    random_id = [tgTool.getRandId()]
                ))
            except telethon.errors.ChannelsTooMuchError as err:
                print(novice.sysTracebackException(ysHasTimestamp = True))
                # 已加入了太多的渠道/超級群組。
                novice.logNeedle.push(
                    '(runId: {}) {} get ChannelsTooMuchError: wait 30 day.'.format(
                        runId, myId
                    )
                )
                maturityDate = novice.dateNowOffset(days = 30)
                tgTool.chanDataNiUsers.pushBandData(myId, maturityDate)
                bandNiUserList.append(myId)

                continue
            except telethon.errors.FloodWaitError as err:
                print(novice.sysTracebackException(ysHasTimestamp = True))
                waitTimeSec = err.seconds
                novice.logNeedle.push(
                    '(runId: {}) {} get FloodWaitError: wait {} seconds.'.format(
                        runId, myId, waitTimeSec
                    )
                )
                # TODO 秒數待驗證
                if waitTimeSec < 180:
                    await asyncio.sleep(waitTimeSec)
                else:
                    maturityDate = novice.dateNowOffset(seconds = waitTimeSec)
                    tgTool.chanDataNiUsers.pushBandData(myId, maturityDate)
                    bandNiUserList.append(myId)

                continue
            except telethon.errors.PeerFloodError as err:
                print(novice.sysTracebackException(ysHasTimestamp = True))
                # 限制發送請求 Too many requests
                novice.logNeedle.push(
                    '(runId: {}) {} get PeerFloodError: wait 1 hour.'.format(runId, myId)
                )
                # TODO 12 小時只是估計值
                maturityDate = novice.dateNowOffset(hours = 12)
                tgTool.chanDataNiUsers.pushBandData(myId, maturityDate)
                bandNiUserList.append(myId)

                continue
            except Exception as err:
                print(novice.sysTracebackException(ysHasTimestamp = True))
                errType = type(err)
                novice.logNeedle.push(
                    '(runId: {}) {} get {} Error: {} (target user: {})'.format(
                        runId, myId, errType, err,
                        peerInfo['name'] \
                            if peerInfo['isHideUsername'] else '@' + peerInfo['username']
                    )
                )
                if novice.indexOf(_invalidMessageErrorTypeList, errType) != -1:
                    novice.logNeedle.push(f'Invalid Message Error({errType}): {err}')
                    break
                elif novice.indexOf(_invalidPeerErrorTypeList, errType) != -1:
                    novice.logNeedle.push(f'Invalid Peer Error({errType}): {err}')
                elif novice.indexOf(_knownErrorTypeList, errType) != -1:
                    novice.logNeedle.push(f'Known Error({errType}): {err}')
                    bandNiUserList.append(myId)
                else:
                    novice.logNeedle.push(f'Unknown Error({errType}): {err}')
                    bandNiUserList.append(myId)

            idx += 1
            if takeUserListLength <= idx:
                break

        latestStatus += ' ({})'.format(
            '仿用戶用盡' if len(bandNiUserList) == usedClientCount else '結束'
        )
        novice.logNeedle.push('(runId: {}) {}'.format(runId, latestStatus))
    except Exception as err:
        latestStatus += ' (失敗)'
        novice.logNeedle.push(f'(runId: {runId}) {latestStatus}')
        raise err
    finally:
        await tgTool.release()


# https://tl.telethon.dev/methods/channels/join_channel.html
# https://tl.telethon.dev/methods/messages/forward_messages.html
_invalidMessageErrorTypeList = [
    telethon.errors.MediaEmptyError,
    telethon.errors.MessageIdsEmptyError,
    telethon.errors.MessageIdInvalidError,
    telethon.errors.RandomIdDuplicateError,
    telethon.errors.RandomIdInvalidError,
    telethon.errors.GroupedMediaInvalidError, # ? Invalid grouped media.
]
_invalidPeerErrorTypeList = [
    ValueError, # 沒有此用戶或群組名稱
    telethon.errors.ChannelInvalidError,
    telethon.errors.ChannelPrivateError,
    telethon.errors.ChatAdminRequiredError,
    telethon.errors.ChatIdInvalidError,
    telethon.errors.ChatSendGifsForbiddenError,
    telethon.errors.ChatSendMediaForbiddenError,
    telethon.errors.ChatSendStickersForbiddenError,
    telethon.errors.ChatWriteForbiddenError,
    telethon.errors.InputUserDeactivatedError,
    telethon.errors.PeerIdInvalidError,
    telethon.errors.UserBannedInChannelError,
    telethon.errors.UserIsBlockedError,
]
_knownErrorTypeList = [
    telethon.errors.PtsChangeEmptyError, # ? No PTS change.
    telethon.errors.ScheduleDateTooLateError,
    telethon.errors.ScheduleTooMuchError,
    telethon.errors.TimeoutError,
    telethon.errors.UserIsBotError,
    telethon.errors.YouBlockedUserError,
]

async def _mentionUsers(
        client: telethon.TelegramClient,
        groupPeer: str,
        users: list,
        greetingTxt: str = '',
        separation: str = ' ') -> typing.List[int]:
    msg = greetingTxt
    entities = []
    sendMessageRequests = []

    # idx = 0
    for user in users:
        name = user.first_name if user.first_name != None else '---'
        if user.last_name != None:
            name += ' ' + user.last_name
        # NOTE: 解決表情字體字數判斷問題
        name = telethon.helpers.add_surrogate(name)

        # NOTE: 每 4096 字符要分段，每提及 99 人要分段
        if len(f'{msg}{separation}{name}') >= 4096 or len(entities) >= 99:
            msg = telethon.helpers.del_surrogate(msg)
            sendMessageRequests.append(telethon.functions.messages.SendMessageRequest(
                peer = groupPeer,
                message = msg,
                entities = entities.copy(),
                random_id = random.randrange(1000000, 9999999)
            ))

            # idx = 0
            msg = greetingTxt
            entities.clear()

        if msg != greetingTxt:
            msg += separation

        # idx += 1
        # msg += str(idx) + '. '

        mentionUser = telethon.types.InputMessageEntityMentionName(
            offset = len(msg),
            length = len(name),
            # NOTE: 用 `telethon.types.InputPeerUser` 也可以耶!
            user_id = telethon.types.InputUser(
                user_id = user.id,
                access_hash = user.access_hash
            )
        )

        msg += name
        entities.append(mentionUser)
        telethon.helpers.del_surrogate(name)

    if len(entities) > 0:
        msg = telethon.helpers.del_surrogate(msg)
        sendMessageRequests.append(telethon.functions.messages.SendMessageRequest(
            peer = groupPeer,
            message = msg,
            entities = entities,
            random_id = random.randrange(1000000, 9999999)
        ))

    messageIds = []
    for sendMessageRequest in sendMessageRequests:
        result = await client(sendMessageRequest)

        for item in result.updates:
            if type(item) != telethon.types.UpdateMessageID:
                continue
            messageIds.append(item.id)
            print(item.id)
            break

    return messageIds

async def _getTargetUsers(
        tgTool: TgBaseTool,
        client: telethon.TelegramClient,
        groupPeer: str,
        msgIds: list) -> typing.List[telethon.types.User]:
    newMsgIds = msgIds.copy()
    newMsgIds.sort(reverse = True)
    msgIdsLength = len(newMsgIds)
    msgId = 0
    limit = 0
    userList = []
    for idx in range(0, msgIdsLength):
        currMsgId = newMsgIds[idx]
        nextMsgId = newMsgIds[idx + 1] if idx + 1 < msgIdsLength else 0

        if msgId == 0:
            msgId = currMsgId
        limit += 1

        if nextMsgId == 0 or currMsgId - nextMsgId != 1:
            result = await client(telethon.functions.messages.GetHistoryRequest(
                peer = groupPeer,
                offset_id = msgId,
                offset_date = 0,
                add_offset = -1,
                limit = limit,
                max_id = 0,
                min_id = 0,
                hash = 0
            ))
            for user in result.users:
                # 排除 自己, 已刪除帳號, 機器人
                if user.is_self or user.deleted or user.bot:
                    continue
                # 排除仿用戶
                if tgTool.lookforClientInfo(user.id) != None:
                    continue

                # 過濾已抓取的
                if user in userList:
                    continue

                userList.append(user)

            msgId = 0
            limit = 0

    return userList

