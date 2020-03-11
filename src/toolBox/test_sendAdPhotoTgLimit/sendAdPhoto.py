#!/usr/bin/env python3


import typing
import os
import datetime
import json
import asyncio
import utils.novice
import utils.json
from tgkream.tgTool import TgBaseTool, telethon


def run(args: list, _dirpy: str, _dirname: str):
    asyncio.run(asyncRun(args, _dirpy, _dirname))

async def asyncRun(args: list, _dirpy: str, _dirname: str):
    url = args[1]
    msg = args[2]

    _env = utils.json.loadYml(_dirname + '/env.yml')

    sendUsersFilePath = os.path.join(_dirpy, 'sendUsers.json')
    if not os.path.exists(sendUsersFilePath):
        raise Exception('疑惑？ "./sendUsers.json" 文件怎麼不見了？')

    forwardPeers = utils.json.load(sendUsersFilePath)

    mainGroup = _env['peers']['adChannle']
    tgTool = TgBaseTool(
        _env['apiId'],
        _env['apiHash'],
        sessionDirPath = _dirname + '/_tgSession',
        clientCount = 1,
        papaPhone = _env['papaPhoneNumber']
    )
    await tgTool.init()

    # messageId = await _sendFile(tgTool, mainGroup, url, msg)
    messageId = 119

    if messageId == -1:
        raise Exception('Use Papa send file fail. (url: {}, msg: {})'.format(url, msg))

    phoneNumber = '+' + (await (await tgTool.pickClient()).get_me()).phone
    print('NiUsers is {}.'.format(phoneNumber))
    logMsg = {
        'im': phoneNumber,
        'time': utils.novice.dateStringify(utils.novice.dateNow()),
        'succ': 0,
        'fail': 0,
        'waitSec': 0,
        'failInfo': [],
    }

    finalPeers = 'hk80808080'
    finalPeersLength = 300
    idx = -1
    async for client in tgTool.iterPickClient(-1, 1):
        idx += 1
        print('{}/{}'.format(idx, finalPeersLength))
        if finalPeersLength <= idx:
            break

        forwardPeer = finalPeers
        # TODO 不太會被封 需再測試才能確定 try cache 語句是否有錯誤
        try:
            typeName = await tgTool.getPeerTypeName(forwardPeer)
            if typeName != 'User':
                await tgTool.joinGroup(client, forwardPeer)

            await client(telethon.functions.messages.SendMessageRequest(
                peer = forwardPeer,
                message = '{} - {}'.format(msg, idx)
            ))

            # inputFile = await client.upload_file(url)
            # await client(telethon.functions.messages.SendMediaRequest(
            #     peer = forwardPeer,
            #     media = telethon.types.InputMediaUploadedPhoto(
            #         file = inputFile,
            #         ttl_seconds = None
            #     ),
            #     message = '{} - {}'.format(msg, idx)
            # ))

            # await client(telethon.functions.messages.ForwardMessagesRequest(
            #     from_peer = mainGroup,
            #     id = [messageId],
            #     to_peer = forwardPeer,
            #     random_id = [tgTool.getRandId()]
            # ))
            logMsg['succ'] += 1
            print('ok {}'.format(forwardPeer))
        except ValueError as err:
            logMsg['failInfo'].append('who: {}, err: ValueError: {}'.format(forwardPeer, err))
            print('沒有此用戶或群組名稱', err)
        except telethon.errors.MessageIdInvalidError as err:
            logMsg['failInfo'].append('who: {}, err: MessageIdInvalidError: {}'.format(forwardPeer, err))
            print('MessageIdInvalidError: {}'.format(err))
            raise err
        except telethon.errors.FloodWaitError as err:
            waitTimeSec = err.seconds
            # logMsg['waitSec'] = waitTimeSec
            # logMsg['failInfo'].append(
            #     'who: {}, phone: {}, err: FloodWaitError: {}'.format(
            #         forwardPeer, phoneNumber, err
            #     )
            # )
            print('FloodWaitError: wait {} seconds.'.format(waitTimeSec))
            # myInfo = await client.get_me()
            # maturityDate = datetime.datetime.now() \
            #     + datetime.timedelta(seconds = waitTimeSec)
            # tgTool.chanDataNiUsers.pushBandData(myInfo.phone, maturityDate)
            await asyncio.sleep(waitTimeSec)
        except telethon.errors.PeerFloodError as err:
            # 限制發送請求 Too many requests
            logMsg['waitSec'] = 3600
            logMsg['failInfo'].append(
                'who: {}, phone: {}, err: PeerFloodError: {}'.format(
                    forwardPeer, phoneNumber, err
                )
            )
            print('PeerFloodError: wait 1 hour.')
            # TODO 1 小時只是估計值
            myInfo = await client.get_me()
            maturityDate = datetime.datetime.now() + datetime.timedelta(hours = 1)
            tgTool.chanDataNiUsers.pushBandData(myInfo.phone, maturityDate)
            break
        except telethon.errors.ChatWriteForbiddenError as err:
            logMsg['failInfo'].append('who: {}, err: ChatWriteForbiddenError: {}'.format(forwardPeer, err))
            # You can't write in this chat
            print('ChatWriteForbiddenError: {}'.format(err))
            tgTool.chanData.pushGuy(
                await client.get_entity(forwardPeer),
                err
            )
        except Exception as err:
            logMsg['failInfo'].append('who: {}, err: {} Error: {} '.format(forwardPeer, type(err), err))
            print('{} Error: {} (target group: {})'.format(type(err), err, forwardPeer))

    logMsg['fail'] = len(logMsg['failInfo'])
    print('\n\n--- 總整理 ---\n{}'.format(utils.json.dump(logMsg)))
    logDataFilePath = os.path.join(_dirpy, 'logData.json')
    if os.path.exists(logDataFilePath):
        logData = utils.json.load(logDataFilePath)
    else:
        logData = []
    logData.append(logMsg)
    utils.json.dump(logData, logDataFilePath)


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
    blackGuyList = tgTool.chanData.get('.blackGuy.list')
    newList = []
    for peer in mainList:
        if utils.novice.indexOf(blackGuyList, peer) == -1:
            newList.append(peer)
    return newList



# async def asyncRun(args: list, _dirpy: str, _dirname: str):
async def AAA(args: list, _dirpy: str, _dirname: str):
    url = args[1]
    msg = args[2]

    _env = utils.json.loadYml(_dirname + '/env.yml')

    sendUsersFilePath = os.path.join(_dirpy, 'sendUsers.json')
    if not os.path.exists(sendUsersFilePath):
        raise Exception('疑惑？ "./sendUsers.json" 文件怎麼不見了？')

    forwardPeers = utils.json.load(sendUsersFilePath)

    mainGroup = _env['peers']['adChannle']
    tgTool = TgBaseTool(
        _env['apiId'],
        _env['apiHash'],
        sessionDirPath = _dirname + '/_tgSession',
        clientCount = 1,
        papaPhone = _env['papaPhoneNumber']
    )
    await tgTool.init()

    messageId = await _sendFile(tgTool, mainGroup, url, msg)

    if messageId == -1:
        raise Exception('Use Papa send file fail. (url: {}, msg: {})'.format(url, msg))

    phoneNumber = '+' + (await (await tgTool.pickClient()).get_me()).phone
    logMsg = {
        'im': phoneNumber,
        'time': utils.novice.dateStringify(utils.novice.dateNow()),
        'succ': 0,
        'fail': 0,
        'waitSec': 0,
        'failInfo': [],
    }

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
            logMsg['succ'] += 1
            print('ok {}'.format(forwardPeer))
        except ValueError as err:
            logMsg['failInfo'].append('who: {}, err: ValueError: {}'.format(forwardPeer, err))
            print('沒有此用戶或群組名稱', err)
        except telethon.errors.MessageIdInvalidError as err:
            logMsg['failInfo'].append('who: {}, err: MessageIdInvalidError: {}'.format(forwardPeer, err))
            print('MessageIdInvalidError: {}'.format(err))
            raise err
        except telethon.errors.FloodWaitError as err:
            waitTimeSec = err.seconds
            logMsg['waitSec'] = waitTimeSec
            logMsg['failInfo'].append(
                'who: {}, phone: {}, err: FloodWaitError: {}'.format(
                    forwardPeer, phoneNumber, err
                )
            )
            print('FloodWaitError: wait {} seconds.'.format(waitTimeSec))
            myInfo = await client.get_me()
            maturityDate = datetime.datetime.now() \
                + datetime.timedelta(seconds = waitTimeSec)
            tgTool.chanDataNiUsers.pushBandData(myInfo.phone, maturityDate)
            break
        except telethon.errors.PeerFloodError as err:
            # 限制發送請求 Too many requests
            logMsg['waitSec'] = 3600
            logMsg['failInfo'].append(
                'who: {}, phone: {}, err: PeerFloodError: {}'.format(
                    forwardPeer, phoneNumber, err
                )
            )
            print('PeerFloodError: wait 1 hour.')
            # TODO 1 小時只是估計值
            myInfo = await client.get_me()
            maturityDate = datetime.datetime.now() + datetime.timedelta(hours = 1)
            tgTool.chanDataNiUsers.pushBandData(myInfo.phone, maturityDate)
            break
        except telethon.errors.ChatWriteForbiddenError as err:
            logMsg['failInfo'].append('who: {}, err: ChatWriteForbiddenError: {}'.format(forwardPeer, err))
            # You can't write in this chat
            print('ChatWriteForbiddenError: {}'.format(err))
            tgTool.chanData.pushGuy(
                await client.get_entity(forwardPeer),
                err
            )
        except Exception as err:
            logMsg['failInfo'].append('who: {}, err: {} Error: {} '.format(forwardPeer, type(err), err))
            print('{} Error: {} (target group: {})'.format(type(err), err, forwardPeer))

    logMsg['fail'] = len(logMsg['failInfo'])
    print('\n\n--- 總整理 ---\n{}'.format(utils.json.dump(logMsg)))
    logDataFilePath = os.path.join(_dirpy, 'logData.json')
    if os.path.exists(logDataFilePath):
        logData = utils.json.load(logDataFilePath)
    else:
        logData = []
    logData.append(logMsg)
    utils.json.dump(logData, logDataFilePath)

