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
    # TODO
    # `client.get_entity` 是一項昂貴的操作
    #   https://docs.telethon.dev/en/latest/modules/client.html#telethon.client.users.UserMethods.get_entity
    #   使用 `client.get_entity` 來解析用戶名是一項昂貴的操作，
    #   若在短時間內請求 50 個用戶名則會引發 "FloodWaitError" 的錯誤。
    # 在實際測試中，在短時間內請求相同的群組名也僅有 200 次的許可。 (2020.02.19 紀錄)
    inputPeer = await client.get_entity(toGroupPeer)
    if type(inputPeer) != telethon.types.User:
        print('--> telethon.functions.channels.JoinChannelRequest')
        await client(telethon.functions.channels.JoinChannelRequest(
            channel = toGroupPeer
        ))

    print('-> 紫爆 Hi')
    pushErrMsg = ''
    async for idx in tgTool.iterLoopInterval(loopTimes, 1):
        try:
            readableIdx = idx + 1
            print('--> {}/{}: {} -> {}'.format(readableIdx, loopTimes, phoneNumber, toGroupPeer))

            print('---> telethon.functions.messages.SendMessageRequest')
            # 在 1970 次請求後需等待 1324 秒 (2020.02.23 紀錄)
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
            # TODO 印象中有短秒數的 FloodWaitError 錯誤
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

