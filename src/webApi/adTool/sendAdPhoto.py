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

    _env = utils.json.loadYml(_dirname + '/env.yml')

    ynContinue = True
    try:
        pageSession['latestStatus'] = '炸群進度： 初始化...'
        tgTool = TgBaseTool(
            _env['apiId'],
            _env['apiHash'],
            sessionDirPath = _dirname + '/' + _env['tgSessionDirPath'],
            clientCount = 1,
            papaPhone = _env['papaPhoneNumber']
        )
        await tgTool.init()
    except Exception as err:
        ynContinue = False
        pageSession['latestStatus'] += ' (失敗)'

    if not ynContinue:
        return

    try:
        finalPeers = _filterGuy(tgTool, forwardPeers)
        finalPeersLength = len(finalPeers)
        idx = -1
        async for client in tgTool.iterPickClient(-1, 1):
            idx += 1
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
            except telethon.errors.MessageIdInvalidError as err:
                print('MessageIdInvalidError: {}'.format(err))
                raise err
            except telethon.errors.FloodWaitError as err:
                waitTimeSec = err.seconds
                print("FloodWaitError: wait {} seconds.".format(waitTimeSec))
                myInfo = await client.get_me()
                maturityDate = datetime.datetime.now() \
                    + datetime.timedelta(seconds = waitTimeSec)
                tgTool.chanDataNiUsers.pushBandData(myInfo.phone, maturityDate)
                await tgTool.reinit()
            except telethon.errors.ChatWriteForbiddenError as err:
                # You can't write in this chat
                print('ChatWriteForbiddenError: {}'.format(err))
                tgTool.chanData.pushGuy(
                    await client.get_entity(forwardPeer),
                    err
                )
            except Exception as err:
                print('{} Error: {} (target group: {})'.format(type(err), err, forwardPeer))

            pageSession['latestStatus'] = '炸群進度： {}/{}'.format(
                idx + 1,
                finalPeersLength
            )
        pageSession['latestStatus'] += ' (結束)'
    except Exception as err:
        pageSession['latestStatus'] += ' (失敗)\n{} Error: {} (target group: {})'.format(type(err), err, forwardPeer)
    finally:
        await tgTool.release()


def _filterGuy(tgTool: TgBaseTool, mainList: typing.List[str]) -> typing.List[str]:
    blackGuyList = tgTool.chanData.data['blackGuy']['list']
    newList = []
    for peer in mainList:
        if utils.novice.indexOf(blackGuyList, peer) == -1:
            newList.append(peer)
    return newList

