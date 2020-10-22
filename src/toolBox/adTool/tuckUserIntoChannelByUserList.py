#!/usr/bin/env python3


import typing
import asyncio
import utils.novice as novice
from tgkream.tgTool import knownError, telethon, TgDefaultInit, TgBaseTool


def run(args: list, _dirpy: str, _dirname: str):
    asyncio.run(asyncRun(args, _dirpy, _dirname))

async def asyncRun(args: list, _dirpy: str, _dirname: str):
    if len(args) < 4:
        raise ValueError('Usage: <usableClientCount> <userPeers> <toGroupPeer>')

    usableClientCount = int(args[1])
    userPeersTxt = args[2]
    toGroupPeer = args[3]

    userPeers = userPeersTxt.split(',')

    tgTool = TgDefaultInit(
        TgBaseTool,
        clientCount = usableClientCount,
        papaPhone = novice.py_env['papaPhoneNumber']
    )
    await tgTool.init()

    print('-> 拉人入群')
    tuckUserIdx = 0
    userPeersLength = len(userPeers)
    pickNiUserList = []
    bandNiUserList = []
    pickUserInfos = {}
    async for clientInfo in tgTool.iterPickClient(-1, 15):
        myId = clientInfo['id']
        client = clientInfo['client']

        if novice.indexOf(bandNiUserList, myId) != -1:
            if len(bandNiUserList) == usableClientCount:
                errMsg = '[tuckUserIntoChannel]: 彷用戶們已盡力'
                logNeedle.push(errMsg)
                raise Exception(errMsg)
            continue

        readableTuckUserIdx = tuckUserIdx + 1
        userPeer = userPeers[tuckUserIdx]

        print('--> {} {}/{} use {} for {} -> {}'.format(
            novice.dateUtcStringify(novice.dateUtcNow()),
            readableTuckUserIdx, userPeersLength,
            myId, userPeer, toGroupPeer
        ))

        if novice.indexOf(pickNiUserList, myId) == -1:
            print('---> niUser join')
            try:
                await tgTool.joinGroup(client, toGroupPeer)
                pickNiUserList.append(myId)
            except telethon.errors.UserAlreadyParticipantError as err:
                # 已經是聊天的參與者。 (私有聊天室)
                pass
            except Exception as err:
                bandNiUserList.append(myId)

                errTypeName = err.__class__.__name__
                errMsg = ''

                if knownError.has('joinGroupMethod', err):
                    errMsg = knownError.getMsg('joinGroupMethod', err)
                else:
                    errMsg = err

                print('{} Error: {} (caused by {})'.format(
                    errTypeName, errMsg, 'tgTool.joinGroup()'
                ))

                continue

        print('---> tuck')
        try:
            await client(telethon.functions.channels.InviteToChannelRequest(
                channel = toGroupPeer,
                users = [userPeer]
            ))
        except telethon.errors.FloodWaitError as err:
            waitTimeSec = err.seconds
            print('FloodWaitError Error: wait {} seconds. (caused by {})'.format(
                waitTimeSec, 'client(channels.InviteToChannelRequest)'
            ))
            if waitTimeSec < 3600:
                print('----> FloodWaitError: wait {} seconds.'.format(waitTimeSec))
                await asyncio.sleep(waitTimeSec + 60)
            else:
                print('----> The +{} phone get FloodWaitError.'.format(myId))
                maturityDate = novice.dateNowOffset(seconds = waitTimeSec)
                tgTool.chanDataNiUsers.pushBandData(myId, maturityDate)
                bandNiUserList.append(myId)

            continue
        except telethon.errors.PeerFloodError as err:
            # 限制發送請求 Too many requests
            print('PeerFloodError Error: {}. (caused by {})'.format(
                err, 'client(channels.InviteToChannelRequest)'
            ))
            print('----> The +{} phone get PeerFloodError.'.format(myId))
            # NOTE: 12 小時只是估計值
            maturityDate = novice.dateNowOffset(hours = 12)
            tgTool.chanDataNiUsers.pushBandData(myId, maturityDate)
            bandNiUserList.append(myId)

            continue
        except Exception as err:
            errTypeName = err.__class__.__name__
            errMsg = ''

            # TODO
            # if novice.indexOf(userBlockedError, errTypeName) != -1:
                # tgTool.chanData.pushGuy(user, err)

            if knownError.has('InviteToChannelRequest', err):
                errMsg = knownError.getMsg('InviteToChannelRequest', err)
            else:
                errMsg = err

            print('{} Error: {} (caused by {})'.format(
                errTypeName, errMsg, 'client(channels.InviteToChannelRequest)'
            ))

        tuckUserIdx += 1
        if tuckUserIdx == userPeersLength:
            break


userBlockedError = [
    # 被用戶拒絕
    'UserBlockedError',
    # 用戶已無法再加入新群
    'UserChannelsTooMuchError',
    # The provided user is not a mutual contact.
    'UserNotMutualContactError',
    # 用戶的隱私設置不允許此行為
    # The user's privacy settings do not allow you to do this. Skipping.
    'UserPrivacyRestrictedError',
]

