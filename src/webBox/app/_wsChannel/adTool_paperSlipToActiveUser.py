#!/usr/bin/env python3


import typing
import random
import asyncio
import utils.novice as novice
import webBox.serverMix as serverMix
from tgkream.tgTool import telethon, TgDefaultInit, TgBaseTool
import webBox.app.utils as appUtils
from webBox.app._wsChannel.niUsersStatus import updateStatus as niUsersStatusUpdateStatus


__all__ = ['paperSlipToActiveUser']


async def paperSlipToActiveUser(pageId: str, wsId: str, prop: typing.Any = None) -> dict:
    innerSession = serverMix.innerSession.get(pageId)
    if innerSession['runing']:
        return {
            'code': -1,
            'message': '工具執行中。',
        }

    if type(prop) != dict:
        return {
            'code': -1,
            'message': '"prop" 參數必須是 `Object` 類型。',
        }
    if not ( \
            'groupPeer' in prop \
            and type(prop['groupPeer']) == str):
        return {
            'code': -1,
            'message': '"prop.groupPeer" 參數不符合預期',
        }
    if not ( \
            'offsetDays' in prop \
            and type(prop['offsetDays']) == int):
        return {
            'code': -1,
            'message': '"prop.offsetDays" 參數不符合預期',
        }
    if not ( \
            'usedNiUserCount' in prop \
            and type(prop['usedNiUserCount']) == int):
        return {
            'code': -1,
            'message': '"prop.usedNiUserCount" 參數不符合預期',
        }
    if not ( \
            'forwardMessageGroup' in prop \
            and type(prop['forwardMessageGroup']) == str):
        return {
            'code': -1,
            'message': '"prop.forwardMessageGroup" 參數不符合預期',
        }
    if not ( \
            'forwardMessageId' in prop \
            and type(prop['forwardMessageId']) == int):
        return {
            'code': -1,
            'message': '"prop.forwardMessageId" 參數不符合預期',
        }

    innerSession['runing'] = True
    asyncio.ensure_future(_paperSlipToActiveUserAction(pageId, innerSession, prop))
    return {
        'code': 0,
        'message': '請求已接收。'
    }

async def _paperSlipToActiveUserAction(pageId: str, innerSession: dict, data: dict):
    groupPeer = data['groupPeer']
    offsetDays = data['offsetDays']
    usedNiUserCount = data['usedNiUserCount']
    forwardMessageGroup = data['forwardMessageGroup']
    forwardMessageId = data['forwardMessageId']

    niUsersStatusInfo = await appUtils.getNiUsersStatusInfo()
    usableNiUsersCount = niUsersStatusInfo['usableCount']
    if usableNiUsersCount < usedNiUserCount:
        innerSession['runing'] = False
        await _paperSlipToActiveUserAction_send(
            pageId, -1, '仿用戶數量不足 (工具目前無法使用)。'
        )
        return

    niUserChannlePeer = novice.py_env['peers']['niUserChannle']

    # 用於打印日誌
    runId = random.randrange(1000000, 9999999)
    usedClientCount = usedNiUserCount
    latestStatus = ''
    try:
        latestStatus = '炸群進度： 初始化...'
        novice.logNeedle.push(f'(runId: {runId}) {latestStatus}')
        await _paperSlipToActiveUserAction_send(pageId, 1, latestStatus)

        tgTool = appUtils.getTgTool(usedClientCount)
        await tgTool.init()
        usedClientCount = tgTool.clientCount
    except Exception as err:
        innerSession['runing'] = False
        latestStatus += ' (失敗)'
        novice.logNeedle.push('(runId: {}) {}'.format(runId, latestStatus))
        await _paperSlipToActiveUserAction_send(pageId, -1, latestStatus, isError = True)
        return

    await niUsersStatusUpdateStatus(usableCount = -1 * usedClientCount)

    isNotPublicGroup = False
    try:
        latestStatus = '炸群進度： 取得前置資料...'
        novice.logNeedle.push(f'(runId: {runId}) {latestStatus}')
        await _paperSlipToActiveUserAction_send(pageId, 1, latestStatus)

        _, isPrivate = telethon.utils.parse_username(groupPeer)
        if isPrivate:
            novice.logNeedle.push(f'(runId: {runId}) 請提供公開群組')
            await _paperSlipToActiveUserAction_send(pageId, 1, '請提供公開群組')
            isNotPublicGroup = True
            raise Exception('請提供公開群組。')
        peerInfo = await tgTool.parsePeer(groupPeer)
        if peerInfo['isGroup'] == False:
            novice.logNeedle.push(f'(runId: {runId}) 請提供公開群組')
            await _paperSlipToActiveUserAction_send(pageId, 1, '請提供公開群組')
            isNotPublicGroup = True
            raise Exception('請提供公開群組。')

        async with tgTool.usePapaClient() as client:
            speakUsers = await tgTool.getSpeakers(
                client = client,
                groupPeer = groupPeer,
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
        innerSession['runing'] = False
        await niUsersStatusUpdateStatus(usableCount = usedClientCount)

        latestStatus += ' (失敗)'
        novice.logNeedle.push(f'(runId: {runId}) {latestStatus}')
        if not isNotPublicGroup:
            appUtils.console.catchError(runId, '取得前置資料')
        await _paperSlipToActiveUserAction_send(
            pageId, -1, latestStatus, isError = not isNotPublicGroup
        )
        return

    takeUserListLength = -1
    try:
        latestStatus = '炸群進度： 同步資料...'
        novice.logNeedle.push(f'(runId: {runId}) {latestStatus}')
        await _paperSlipToActiveUserAction_send(pageId, 1, latestStatus)

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
        innerSession['runing'] = False
        await niUsersStatusUpdateStatus(usableCount = usedClientCount)

        latestStatus += ' (失敗)'
        novice.logNeedle.push(f'(runId: {runId}) {latestStatus}')
        appUtils.console.catchError(runId, '同步資料')
        await _paperSlipToActiveUserAction_send(pageId, -1, latestStatus, isError = True)
        return

    try:
        bandNiUserList = []
        idx = 0
        async for clientInfo in tgTool.iterPickClient(-1, 1):
            readableIdx = idx + 1
            myId = clientInfo['id']
            client = clientInfo['client']

            if novice.indexOf(bandNiUserList, myId) != -1:
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
                await _paperSlipToActiveUserAction_send(pageId, 1, latestStatus)

                inputEntity = telethon.types.InputPeerUser(
                    user_id = forwardUser.id,
                    access_hash = forwardUser.access_hash
                )
                await client(telethon.functions.messages.ForwardMessagesRequest(
                    from_peer = forwardMessageGroup,
                    id = [forwardMessageId],
                    to_peer = inputEntity,
                    random_id = [tgTool.getRandId()]
                ))
            except telethon.errors.ChannelsTooMuchError as err:
                # 已加入了太多的渠道/超級群組。
                errMsg = '{myId} get ChannelsTooMuchError: wait 30 day.'
                novice.logNeedle.push(f'(runId: {runId}) {errMsg}')
                await _paperSlipToActiveUserAction_send(pageId, -1, errMsg)
                maturityDate = novice.dateNowOffset(days = 30)
                tgTool.chanDataNiUsers.pushBandData(myId, maturityDate)
                bandNiUserList.append(myId)

                continue
            except telethon.errors.FloodWaitError as err:
                waitTimeSec = err.seconds
                errMsg = f'{myId} get FloodWaitError: wait {waitTimeSec} seconds.'
                novice.logNeedle.push(f'(runId: {runId}) {errMsg}')
                await _paperSlipToActiveUserAction_send(pageId, -1, errMsg)
                # TODO 秒數待驗證
                if waitTimeSec < 180:
                    await asyncio.sleep(waitTimeSec)
                else:
                    maturityDate = novice.dateNowOffset(seconds = waitTimeSec)
                    tgTool.chanDataNiUsers.pushBandData(myId, maturityDate)
                    bandNiUserList.append(myId)

                continue
            except telethon.errors.PeerFloodError as err:
                # 限制發送請求 Too many requests
                errMsg = f'{myId} get PeerFloodError: wait 12 hour.'
                novice.logNeedle.push(f'(runId: {runId}) {errMsg}')
                await _paperSlipToActiveUserAction_send(pageId, -1, errMsg)
                # TODO 12 小時只是估計值
                maturityDate = novice.dateNowOffset(hours = 12)
                tgTool.chanDataNiUsers.pushBandData(myId, maturityDate)
                bandNiUserList.append(myId)

                continue
            except Exception as err:
                errType = type(err)
                novice.logNeedle.push(
                    '(runId: {}) {} get {} Error: {} (target user: {})'.format(
                        runId, myId, errType, err,
                        peerInfo['name'] \
                            if peerInfo['isHideUsername'] else '@' + peerInfo['username']
                    )
                )
                if novice.indexOf(_invalidMessageErrorTypeList, errType) != -1:
                    errMsg = f'Invalid Message Error({errType}): {err}'
                    novice.logNeedle.push(f'(runId: {runId}) {errMsg}')
                    await _paperSlipToActiveUserAction_send(pageId, -1, errMsg)
                    break
                elif novice.indexOf(_invalidPeerErrorTypeList, errType) != -1:
                    errMsg = f'Invalid Peer Error({errType}): {err}'
                    novice.logNeedle.push(f'(runId: {runId}) {errMsg}')
                    await _paperSlipToActiveUserAction_send(pageId, -1, errMsg)
                elif novice.indexOf(_knownErrorTypeList, errType) != -1:
                    errMsg = f'Known Error({errType}): {err}'
                    novice.logNeedle.push(f'(runId: {runId}) {errMsg}')
                    await _paperSlipToActiveUserAction_send(pageId, -1, errMsg)
                    bandNiUserList.append(myId)
                else:
                    errMsg = f'Unknown Error({errType}): {err}'
                    novice.logNeedle.push(f'(runId: {runId}) {errMsg}')
                    await _paperSlipToActiveUserAction_send(pageId, -1, errMsg)
                    bandNiUserList.append(myId)

            idx += 1
            if takeUserListLength <= idx:
                break

        latestStatus += ' ({})'.format(
            '仿用戶用盡' if len(bandNiUserList) == usedClientCount else '結束'
        )
        novice.logNeedle.push('(runId: {}) {}'.format(runId, latestStatus))
        await _paperSlipToActiveUserAction_send(pageId, 1, latestStatus)
    except Exception as err:
        latestStatus += ' (失敗)'
        novice.logNeedle.push(f'(runId: {runId}) {latestStatus}')
        await _paperSlipToActiveUserAction_send(pageId, -1, latestStatus, isError = True)
    finally:
        await tgTool.release()
        innerSession['runing'] = False
        await niUsersStatusUpdateStatus(usableCount = usedClientCount)


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

async def _paperSlipToActiveUserAction_send(
        pageId: str,
        code: int,
        message: str,
        isError = False) -> None:
    payload = {
        'code': code,
        'message': message,
    }
    if isError:
        errInfo = novice.sysExceptionInfo()
        errMsg = novice.sysTracebackException()
        payload['message'] += '\n' + errMsg
        payload['catchError'] = {
            'name': errInfo['name'],
            'message': errInfo['message'],
            'stackList': errInfo['stackList'],
        }
    await serverMix.wsHouse.send(pageId, fnResult = {
        'name': 'adTool.paperSlipToActiveUserAction',
        'result': payload,
    })

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

