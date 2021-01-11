#!/usr/bin/env python3


import typing
import random
import asyncio
import utils.novice as novice
import webBox.serverMix as serverMix
from tgkream.tgTool import telethon, TgDefaultInit, TgBaseTool
import webBox.app.utils as appUtils
from webBox.app._wsChannel.niUsersStatus import updateStatus as niUsersStatusUpdateStatus


__all__ = ['paperSlip']


async def paperSlip(pageId: str, wsId: str, prop: typing.Any = None) -> dict:
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
            'forwardPeerList' in prop \
            and type(prop['forwardPeerList']) == list):
        return {
            'code': -1,
            'message': '"prop.forwardPeerList" 參數不符合預期',
        }
    if not ( \
            'mainGroup' in prop \
            and type(prop['mainGroup']) == str):
        return {
            'code': -1,
            'message': '"prop.mainGroup" 參數不符合預期',
        }
    if not ( \
            'messageId' in prop \
            and type(prop['messageId']) == int):
        return {
            'code': -1,
            'message': '"prop.messageId" 參數不符合預期',
        }

    innerSession['runing'] = True
    asyncio.ensure_future(_paperSlipAction(pageId, innerSession, prop))
    return {
        'code': 0,
        'message': '請求已接收。'
    }

async def _paperSlipAction(pageId: str, innerSession: dict, data: dict):
    niUsersStatusInfo = await appUtils.getNiUsersStatusInfo()
    usableNiUsersCount = niUsersStatusInfo['usableCount']
    if usableNiUsersCount < 3:
        innerSession['runing'] = False
        await _paperSlipAction_send(pageId, -1, '工具目前無法使用。')
        return

    forwardPeers = data['forwardPeerList']
    mainGroup = data['mainGroup']
    messageId = data['messageId']

    # 用於打印日誌
    runId = random.randrange(1000000, 9999999)
    usedClientCount = int(usableNiUsersCount / 4)
    latestStatus = ''
    try:
        latestStatus = '炸群進度： 初始化...'
        novice.logNeedle.push('(runId: {}) {}'.format(runId, latestStatus))
        await _paperSlipAction_send(pageId, 1, latestStatus)

        tgTool = appUtils.getTgTool(usedClientCount)
        await tgTool.init()
        usedClientCount = tgTool.clientCount
    except Exception as err:
        innerSession['runing'] = False
        latestStatus += ' (失敗)'
        novice.logNeedle.push('(runId: {}) {}'.format(runId, latestStatus))
        await _paperSlipAction_send(pageId, -1, latestStatus, isError = True)
        return

    await niUsersStatusUpdateStatus(usableCount = -1 * usedClientCount)

    try:
        finalPeers = _filterGuy(tgTool, forwardPeers)
        finalPeersLength = len(finalPeers)
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

            if finalPeersLength <= idx:
                break

            latestStatus = '炸群進度： {}/{}'.format(readableIdx, finalPeersLength)
            novice.logNeedle.push('(runId: {}) ok: {}/{}'.format(
                runId, readableIdx, finalPeersLength
            ))
            await _paperSlipAction_send(pageId, 1, latestStatus)
            try:
                forwardPeer = finalPeers[idx]

                inputEntity = await client.get_input_entity(forwardPeer)
                novice.logNeedle.push(f'(runId: {runId}) {type(inputEntity)}.')
                if type(inputEntity) != telethon.types.InputPeerUser:
                    await tgTool.joinGroup(client, forwardPeer)

                await client(telethon.functions.messages.ForwardMessagesRequest(
                    from_peer = mainGroup,
                    id = [messageId],
                    to_peer = forwardPeer,
                    random_id = [tgTool.getRandId()]
                ))

                idx += 1
            except telethon.errors.ChannelsTooMuchError as err:
                # 已加入了太多的渠道/超級群組。
                novice.logNeedle.push(
                    '(runId: {}) {} get ChannelsTooMuchError: wait 30 day.'.format(
                        runId, myId
                    )
                )
                maturityDate = novice.dateNowOffset(days = 30)
                tgTool.chanDataNiUsers.pushBandData(myId, maturityDate)
                bandNiUserList.append(myId)
            except telethon.errors.FloodWaitError as err:
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
            except telethon.errors.PeerFloodError as err:
                # 限制發送請求 Too many requests
                novice.logNeedle.push(
                    '(runId: {}) {} get PeerFloodError: wait 12 hour.'.format(runId, myId)
                )
                # TODO 12 小時只是估計值
                maturityDate = novice.dateNowOffset(hours = 12)
                tgTool.chanDataNiUsers.pushBandData(myId, maturityDate)
                bandNiUserList.append(myId)
            except Exception as err:
                errType = type(err)
                novice.logNeedle.push(
                    '(runId: {}) {} get {} Error: {} (target group: {})'.format(
                        runId, myId, errType, err, forwardPeer
                    )
                )
                if novice.indexOf(_invalidMessageErrorTypeList, errType) != -1:
                    novice.logNeedle.push(
                        'Invalid Message Error({}): {}'.format(errType, err)
                    )
                    break
                elif novice.indexOf(_invalidPeerErrorTypeList, errType) != -1:
                    novice.logNeedle.push(
                        'Invalid Peer Error({}): {}'.format(errType, err)
                    )
                    idx += 1
                elif novice.indexOf(_knownErrorTypeList, errType) != -1:
                    novice.logNeedle.push(
                        'Known Error({}): {}'.format(errType, err)
                    )
                    idx += 1
                    bandNiUserList.append(myId)
                else:
                    novice.logNeedle.push(
                        'Unknown Error({}): {}'.format(type(err), err)
                    )
                    idx += 1
                    bandNiUserList.append(myId)

        latestStatus += ' ({})'.format(
            '仿用戶用盡' if len(bandNiUserList) == usedClientCount else '結束'
        )
        novice.logNeedle.push('(runId: {}) {}'.format(runId, latestStatus))
        await _paperSlipAction_send(pageId, 1, latestStatus)
    except Exception as err:
        latestStatus += ' (失敗)'
        novice.logNeedle.push('(runId: {}) {}'.format(runId, latestStatus))
        await _paperSlipAction_send(pageId, -1, latestStatus, isError = True)
    finally:
        innerSession['runing'] = False
        await niUsersStatusUpdateStatus(usableCount = usedClientCount)
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

async def _paperSlipAction_send(
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
        'name': 'adTool.paperSlipAction',
        'result': payload,
    })

def _filterGuy(tgTool: TgBaseTool, mainList: typing.List[str]) -> typing.List[str]:
    blackGuyList = tgTool.chanData.data['blackGuy']['list']
    newList = []
    for peer in mainList:
        if novice.indexOf(blackGuyList, peer) == -1:
            newList.append(peer)
    return newList

