#!/usr/bin/env python3


import typing
import os
import random
import asyncio
import json
import utils.novice as novice
from tgkream.tgTool import telethon, TgDefaultInit, TgBaseTool


def run(args: list, _dirpy: str, _dirname: str):
    asyncio.run(asyncRun(args, _dirpy, _dirname))

async def asyncRun(args: list, _dirpy: str, _dirname: str):
    forwardPeersTxt = args[1]
    url = args[2]
    msg = args[3]

    mainGroup = novice.py_env['peers']['adChannle']
    forwardPeers = forwardPeersTxt.split(',')

    # 用於打印日誌
    runId = random.randrange(1000000, 9999999)
    usedClientCount = 3
    latestStatus = ''
    try:
        latestStatus = '炸群進度： 初始化...'
        novice.logNeedle.push('(runId: {}) {}'.format(runId, latestStatus))
        tgTool = TgDefaultInit(
            TgBaseTool,
            clientCount = 3,
            papaPhone = novice.py_env['papaPhoneNumber']
        )
        await tgTool.init()
    except Exception as err:
        latestStatus += ' (失敗)'
        novice.logNeedle.push('(runId: {}) {}'.format(runId, latestStatus))
        raise err

    try:
        latestStatus = '炸群進度： 上傳圖片...'
        novice.logNeedle.push('(runId: {}) {}'.format(runId, latestStatus))
        messageId = await _sendFile(tgTool, mainGroup, url, msg)

        if messageId == -1:
            raise Exception('Use Papa send file fail. (url: {}, msg: {})'.format(url, msg))
    except Exception as err:
        latestStatus += ' (失敗)'
        novice.logNeedle.push('(runId: {}) {}'.format(runId, latestStatus))
        raise err

    try:
        finalPeers = _filterGuy(tgTool, forwardPeers)
        finalPeersLength = len(finalPeers)
        bandNiUserList = []
        idx = 0
        async for clientInfo in tgTool.iterPickClient(-1, 1, whichNiUsers = True):
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
            try:
                forwardPeer = finalPeers[idx]
                await tgTool.joinGroup(client, forwardPeer)
                await client(telethon.functions.messages.ForwardMessagesRequest(
                    from_peer = mainGroup,
                    id = [messageId],
                    to_peer = forwardPeer,
                    random_id = [tgTool.getRandId()]
                ))

                idx += 1
            except telethon.errors.ChannelsTooMuchError as err:
                print(novice.sysTracebackException(ysHasTimestamp = True))
                # 已加入了太多的渠道/超級群組。
                novice.logNeedle.push(
                    '(runId: {}) {} get ChannelsTooMuchError: wait 30 day.'.format(
                        runId, myId
                    )
                )
                maturityDate = novice.dateNowAfter(days = 30)
                tgTool.chanDataNiUsers.pushBandData(myId, maturityDate)
                bandNiUserList.append(myId)
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
                    maturityDate = novice.dateNowAfter(seconds = waitTimeSec)
                    tgTool.chanDataNiUsers.pushBandData(myId, maturityDate)
                    bandNiUserList.append(myId)
            except telethon.errors.PeerFloodError as err:
                print(novice.sysTracebackException(ysHasTimestamp = True))
                # 限制發送請求 Too many requests
                novice.logNeedle.push(
                    '(runId: {}) {} get PeerFloodError: wait 1 hour.'.format(runId, myId)
                )
                # TODO 12 小時只是估計值
                maturityDate = novice.dateNowAfter(hours = 12)
                tgTool.chanDataNiUsers.pushBandData(myId, maturityDate)
                bandNiUserList.append(myId)
            except Exception as err:
                print(novice.sysTracebackException(ysHasTimestamp = True))
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
    except Exception as err:
        latestStatus += ' (失敗)'
        novice.logNeedle.push('(runId: {}) {}'.format(runId, latestStatus))
        raise err


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

async def _sendFile(tgTool: TgBaseTool, group: str, url: str, msg: str = '') -> int:
    async with tgTool.usePapaClient() as client:
        inputFile = await client.upload_file(url)

        rtnUpdates = await client(telethon.functions.messages.SendMediaRequest(
            peer = group,
            media = telethon.types.InputMediaUploadedPhoto(
                file = inputFile,
                ttl_seconds = None
            ),
            message = msg
        ))

        messageId = -1
        for update in rtnUpdates.updates:
            if type(update) == telethon.types.UpdateMessageID:
                messageId = update.id
                break

    return messageId

def _filterGuy(tgTool: TgBaseTool, mainList: typing.List[str]) -> typing.List[str]:
    blackGuyList = tgTool.chanData.data['blackGuy']['list']
    newList = []
    for peer in mainList:
        if novice.indexOf(blackGuyList, peer) == -1:
            newList.append(peer)
    return newList

