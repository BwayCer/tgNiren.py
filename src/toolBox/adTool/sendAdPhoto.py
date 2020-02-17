#!/usr/bin/env python3


import typing
import os
import json
import asyncio
import utils.novice
import utils.json
from tgkream.tgTool import TgBaseTool, telethon


def run(args: list, _dirpy: str, _dirname: str):
    asyncio.run(asyncRun(args, _dirpy, _dirname))

async def asyncRun(args: list, _dirpy: str, _dirname: str):
    data = json.loads(args[1])

    _env = utils.json.loadYml(_dirname + '/env.yml')

    forwardPeers = data['forwardPeerList']
    url = data['url']
    msg = data['msg']

    mainGroup = _env['peers']['adChannle']
    tgTool = TgBaseTool(
        _env['apiId'],
        _env['apiHash'],
        sessionDirPath = _dirname + '/_tgSession',
        clientCount = 3,
        papaPhone = _env['papaPhoneNumber']
    )
    await tgTool.init()

    messageId = await _sendFile(tgTool, mainGroup, url, msg)

    if messageId == -1:
        raise Exception('Use Papa send file fail. (url: {}, msg: {})'.format(url, msg))

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
            maturityDate = utils.novice.dateNowAfter(seconds = waitTimeSec)
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
        if utils.novice.indexOf(blackGuyList, peer) == -1:
            newList.append(peer)
    return newList

