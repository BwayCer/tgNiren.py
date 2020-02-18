#!/usr/bin/env python3


import typing
import asyncio
import utils.novice
import utils.json
from tgkream.tgSimple import telethon, TgSimple


def run(args: list, _dirpy: str, _dirname: str):
    asyncio.run(asyncRun(args, _dirpy, _dirname))

async def asyncRun(args: list, _dirpy: str, _dirname: str):
    if len(args) < 4:
        raise ValueError('Usage: <phoneNumber> <loopTimes> <toGroupPeer>')

    phoneNumber = args[1]
    loopTimes = int(args[2])
    toGroupPeer = args[3]

    _env = utils.json.loadYml(_dirname + '/env.yml')

    tgTool = TgSimple(
        _env['apiId'],
        _env['apiHash'],
        sessionDirPath = _dirname + '/' + _env['tgSessionDirPath'],
    )

    print('-> 登入用戶')
    client = await tgTool.login(phoneNumber)
    myInfo = await client.get_me()
    print('--> I\m {} {} ({}) and my phone is +{}.'.format(
        str(myInfo.first_name),
        str(myInfo.last_name),
        str(myInfo.username),
        myInfo.phone,
    ))

    print('-> 加入聊天室')
    # 會受 telethon.errors.FloodWaitError 影響
    inputPeer = await client.get_entity(toGroupPeer)
    if type(inputPeer) != telethon.types.User:
        print('--> telethon.functions.channels.JoinChannelRequest')
        await client(telethon.functions.channels.JoinChannelRequest(
            channel = toGroupPeer
        ))

    print('-> 紫爆 Hi')
    pushErrMsg = ''
    async for idx in tgTool.iterLoopInterval(loopTimes, 1):
        # TODO 不太會被封 需再測試才能確定 try cache 語句是否有錯誤
        try:
            readableIdx = idx + 1
            print('--> {}/{}: {} -> {}'.format(readableIdx, loopTimes, phoneNumber, toGroupPeer))

            print('---> telethon.functions.messages.SendMessageRequest')
            await client(telethon.functions.messages.SendMessageRequest(
                peer = toGroupPeer,
                message = 'PurplePink {}{}'.format(
                    readableIdx,
                    '\n' + pushErrMsg if pushErrMsg != '' else ''
                ),
                random_id = tgTool.getRandId()
            ))
            pushErrMsg = ''
        except ValueError as err:
            print(utils.novice.sysTracebackException(ysHasTimestamp = True))
            print('ValueError(沒有此用戶或群組名稱): {}'.format(err))
            break
        except telethon.errors.MessageIdInvalidError as err:
            print(utils.novice.sysTracebackException(ysHasTimestamp = True))
            print('MessageIdInvalidError: {}'.format(err))
            raise err
        except telethon.errors.FloodWaitError as err:
            print(utils.novice.sysTracebackException(ysHasTimestamp = True))
            waitTimeSec = err.seconds
            # TODO 秒數待驗證
            print('FloodWaitError: {}'.format(err))
            if waitTimeSec < 720:
                print('---> FloodWaitError: wait {} seconds.'.format(waitTimeSec))
                await asyncio.sleep(waitTimeSec)
                pushErrMsg = 'FloodWaitError: wait {} seconds.'
            else:
                break
        except telethon.errors.PeerFloodError as err:
            # 限制發送請求 Too many requests
            print(utils.novice.sysTracebackException(ysHasTimestamp = True))
            print('PeerFloodError: {}'.format(err))
            break
        except telethon.errors.ChatWriteForbiddenError as err:
            # You can't write in this chat
            print(utils.novice.sysTracebackException(ysHasTimestamp = True))
            print('ChatWriteForbiddenError: {}'.format(err))
            break
        except Exception as err:
            print(utils.novice.sysTracebackException(ysHasTimestamp = True))
            print('{} Error: {} '.format(type(err), err))
            break

