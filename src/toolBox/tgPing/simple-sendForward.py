#!/usr/bin/env python3


import typing
import re
import asyncio
import utils.novice as novice
from tgkream.tgSimple import telethon, TgDefaultInit, TgSimple


def run(args: list, _dirpy: str, _dirname: str):
    asyncio.run(asyncRun(args, _dirpy, _dirname))

async def asyncRun(args: list, _dirpy: str, _dirname: str):
    if len(args) < 5:
        raise ValueError('Usage: <phoneNumber> <loopTimes> <toGroupPeer> <forwardLink>')

    phoneNumber = args[1]
    loopTimes = int(args[2])
    toGroupPeer = args[3]
    forwardLink = args[4]

    regexForwardLink = r'^https:\/\/t\.me\/([^\/]+)\/(\d+)$'
    matchForwardLink = re.search(regexForwardLink, forwardLink)
    if not matchForwardLink:
        raise ValueError('轉傳來源鏈結 "{}" 不如預期'.format(forwardLink))
    forwardGroup = matchForwardLink.group(1)
    forwardMessageId = int(matchForwardLink.group(2))

    tgTool = TgDefaultInit(TgSimple)

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
    inputPeer = await client.get_entity(toGroupPeer)
    if type(inputPeer) != telethon.types.User:
        print('--> telethon.functions.channels.JoinChannelRequest')
        await client(telethon.functions.channels.JoinChannelRequest(
            channel = toGroupPeer
        ))

    print('-> 紫爆轉傳 Hi')
    async for idx in tgTool.iterLoopInterval(loopTimes, 1):
        try:
            readableIdx = idx + 1
            print('--> {}/{}: {} -> {}'.format(readableIdx, loopTimes, phoneNumber, toGroupPeer))

            print('---> telethon.functions.messages.SendMessageRequest')
            await client(telethon.functions.messages.ForwardMessagesRequest(
                from_peer = forwardGroup,
                id = [forwardMessageId],
                to_peer = toGroupPeer,
                random_id = [tgTool.getRandId()]
            ))
        except telethon.errors.FloodWaitError as err:
            print(novice.sysTracebackException(ysHasTimestamp = True))
            waitTimeSec = err.seconds
            print('FloodWaitError: wait {} seconds. {}'.format(waitTimeSec, err))
            break
        except telethon.errors.PeerFloodError as err:
            # 限制發送請求 Too many requests
            print(novice.sysTracebackException(ysHasTimestamp = True))
            print('PeerFloodError: {}'.format(err))
            break
        except telethon.errors.UserIsBlockedError as err:
            # User is blocked
            print(novice.sysTracebackException(ysHasTimestamp = True))
            print('UserIsBlockedError: {}'.format(err))
            break
        except Exception as err:
            print(novice.sysTracebackException(ysHasTimestamp = True))
            errType = type(err)
            if novice.indexOf(_invalidMessageErrorTypeList, errType) == -1:
                print('Invalid Error({}): {}'.format(errType, err))
            elif novice.indexOf(_knownErrorTypeList, errType) == -1:
                print('Known Error({}): {}'.format(errType, err))
                break
            else:
                print('Unknown Error({}): {}'.format(type(err), err))
                break


# https://tl.telethon.dev/methods/messages/forward_messages.html
_invalidMessageErrorTypeList = [
    telethon.errors.MediaEmptyError,
    telethon.errors.MessageIdsEmptyError,
    telethon.errors.MessageIdInvalidError,
    telethon.errors.RandomIdDuplicateError,
    telethon.errors.RandomIdInvalidError,
]
_knownErrorTypeList = [
    ValueError, # 沒有此用戶或群組名稱
    telethon.errors.ChannelInvalidError,
    telethon.errors.ChannelPrivateError,
    telethon.errors.ChatAdminRequiredError,
    telethon.errors.ChatIdInvalidError,
    telethon.errors.ChatSendGifsForbiddenError,
    telethon.errors.ChatSendMediaForbiddenError,
    telethon.errors.ChatSendStickersForbiddenError,
    telethon.errors.ChatWriteForbiddenError,
    telethon.errors.GroupedMediaInvalidError, # ? Invalid grouped media.
    telethon.errors.InputUserDeactivatedError,
    telethon.errors.PeerIdInvalidError,
    telethon.errors.PtsChangeEmptyError,
    telethon.errors.ScheduleDateTooLateError,
    telethon.errors.ScheduleTooMuchError,
    telethon.errors.TimeoutError,
    telethon.errors.UserBannedInChannelError,
    telethon.errors.UserIsBotError,
    telethon.errors.YouBlockedUserError,
]

