#!/usr/bin/env python3


import typing
import os
import datetime
import asyncio
import utils.novice as novice
from tgkream.tgTool import TgBaseTool, telethon


async def asyncRun(pageSession: dict, data: dict, _dirname: str):
    forwardPeers = data['forwardPeerList']
    mainGroup = data['mainGroup']
    messageId = data['messageId']

    if type(forwardPeers) != list or type(mainGroup) != str or type(messageId) != int:
        pageSession['latestStatus'] = '參數錯誤，無法運行命令。'
        return

    pageSession['runing'] = True

    ynContinue = True
    usedClientCount = 3
    try:
        pageSession['latestStatus'] = '炸群進度： 初始化...'
        tgTool = TgBaseTool(
            novice.py_env['apiId'],
            novice.py_env['apiHash'],
            sessionDirPath = _dirname + '/' + novice.py_env['tgSessionDirPath'],
            clientCount = usedClientCount,
            papaPhone = novice.py_env['papaPhoneNumber']
        )
        await tgTool.init()
    except Exception as err:
        ynContinue = False
        pageSession['latestStatus'] += ' (失敗)'

    if not ynContinue:
        pageSession['runing'] = False
        return

    try:
        # 用於打印日誌
        runId = tgTool.getRandId()
        finalPeers = _filterGuy(tgTool, forwardPeers)
        finalPeersLength = len(finalPeers)
        bandNiUserList = []
        idx = 0
        # TODO 越來越容易被封 但至少也能傳近乎 200 則 所以暫且不先延長時間
        async for clientInfo in tgTool.iterPickClient(-1, 1, whichNiUsers = True):
            myId = clientInfo['id']
            client = clientInfo['client']

            if novice.indexOf(bandNiUserList, myId) != -1:
                if len(bandNiUserList) == usedClientCount:
                    break
                continue

            if finalPeersLength <= idx:
                break

            forwardPeer = finalPeers[idx]
            try:
                typeName = await tgTool.getPeerTypeName(forwardPeer)
                if typeName != 'User':
                    await tgTool.joinGroup(client, forwardPeer)

                await client(telethon.functions.messages.ForwardMessagesRequest(
                    from_peer = mainGroup,
                    id = [messageId],
                    to_peer = forwardPeer,
                    random_id = [tgTool.getRandId()]
                ))

                idx += 1
                pageSession['latestStatus'] = '炸群進度： {}/{}'.format(
                    idx,
                    finalPeersLength
                )
                print('(runId: {}) ok: {}/{}'.format(runId, idx, finalPeersLength))
            except telethon.errors.MessageIdInvalidError as err:
                print('(runId: {}) {} get MessageIdInvalidError: {}'.format(
                    runId, myId, err
                ))
                raise err
            except telethon.errors.FloodWaitError as err:
                waitTimeSec = err.seconds
                print('(runId: {}) {} get FloodWaitError: wait {} seconds.'.format(runId, myId, waitTimeSec))
                # TODO 秒數待驗證
                if waitTimeSec < 180:
                    await asyncio.sleep(waitTimeSec)
                else:
                    maturityDate = novice.dateNowAfter(seconds = waitTimeSec)
                    tgTool.chanDataNiUsers.pushBandData(myId, maturityDate)
                    bandNiUserList.append(myId)
            except telethon.errors.PeerFloodError as err:
                # 限制發送請求 Too many requests
                print('(runId: {}) {} get PeerFloodError: wait 1 hour.'.format(runId, myId))
                # TODO 12 小時只是估計值
                maturityDate = novice.dateNowAfter(hours = 12)
                tgTool.chanDataNiUsers.pushBandData(myId, maturityDate)
                bandNiUserList.append(myId)
            except telethon.errors.ChatWriteForbiddenError as err:
                # You can't write in this chat
                print('(runId: {}) {} get ChatWriteForbiddenError: {}'.format(runId, myId, err))
                tgTool.chanData.pushGuy(
                    await client.get_entity(forwardPeer),
                    err
                )
                idx += 1
            except Exception as err:
                print('(runId: {}) {} get {} Error: {} (target group: {})'.format(
                    runId, myId, type(err), err, forwardPeer
                ))
                # 預防性處理，避免相同錯誤一值迴圈
                bandNiUserList.append(myId)

        if len(bandNiUserList) == usedClientCount:
            pageSession['latestStatus'] += ' (仿用戶用盡)'
        else:
            pageSession['latestStatus'] += ' (結束)'
    except Exception as err:
        pageSession['latestStatus'] += ' (失敗)\n{} Error: {} (target group: {})'.format(
            type(err),
            novice.sysTracebackException(),
            forwardPeer
        )
    finally:
        pageSession['runing'] = False
        await tgTool.release()


def _filterGuy(tgTool: TgBaseTool, mainList: typing.List[str]) -> typing.List[str]:
    blackGuyList = tgTool.chanData.data['blackGuy']['list']
    newList = []
    for peer in mainList:
        if novice.indexOf(blackGuyList, peer) == -1:
            newList.append(peer)
    return newList

