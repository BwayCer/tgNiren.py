#!/usr/bin/env python3


import typing
import os
import datetime
import json
import asyncio
import utils.novice
import utils.json
from tgkream.tgTool import TgBaseTool, telethon


async def asyncRun(pageSession: dict, data: dict, _dirname: str):
    forwardPeers = data['forwardPeerList']
    mainGroup = data['mainGroup']
    messageId = data['messageId']

    if type(forwardPeers) != list or type(mainGroup) != str or type(messageId) != int:
        pageSession['latestStatus'] = '參數錯誤，無法運行命令。'
        return

    _env = utils.json.loadYml(_dirname + '/env.yml')

    pageSession['runing'] = True

    ynContinue = True
    try:
        pageSession['latestStatus'] = '炸群進度： 初始化...'
        tgTool = TgBaseTool(
            _env['apiId'],
            _env['apiHash'],
            sessionDirPath = _dirname + '/' + _env['tgSessionDirPath'],
            clientCount = 3,
            papaPhone = _env['papaPhoneNumber']
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
        idx = 0
        async for client in tgTool.iterPickClient(-1, 1):
            if finalPeersLength <= idx:
                break

            forwardPeer = finalPeers[idx]
            # TODO 不太會被封 需再測試才能確定 try cache 語句是否有錯誤
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
                print('(runId: {}) ok: {}/{}'.format(runid, idx, finalPeersLength))
            except telethon.errors.MessageIdInvalidError as err:
                print('(runId: {}) MessageIdInvalidError: {}'.format(runid, err))
                raise err
            except telethon.errors.FloodWaitError as err:
                waitTimeSec = err.seconds
                print('(runId: {}) FloodWaitError: wait {} seconds.'.format(runid, waitTimeSec))
                myId = (await client.get_me()).phone
                maturityDate = utils.novice.dateNowAfter(seconds = waitTimeSec)
                tgTool.chanDataNiUsers.pushBandData(myId, maturityDate)
                await tgTool.reinit()
            except telethon.errors.ChatWriteForbiddenError as err:
                # You can't write in this chat
                print('(runId: {}) ChatWriteForbiddenError: {}'.format(runid, err))
                tgTool.chanData.pushGuy(
                    await client.get_entity(forwardPeer),
                    err
                )
                idx += 1
            except Exception as err:
                print('(runId: {}) {} Error: {} (target group: {})'.format(
                    runid, type(err), err, forwardPeer
                ))
                idx += 1

        pageSession['latestStatus'] += ' (結束)'
    except Exception as err:
        pageSession['latestStatus'] += ' (失敗)\n{} Error: {} (target group: {})'.format(type(err), err, forwardPeer)
    finally:
        pageSession['runing'] = False
        await tgTool.release()


def _filterGuy(tgTool: TgBaseTool, mainList: typing.List[str]) -> typing.List[str]:
    blackGuyList = tgTool.chanData.data['blackGuy']['list']
    newList = []
    for peer in mainList:
        if utils.novice.indexOf(blackGuyList, peer) == -1:
            newList.append(peer)
    return newList

