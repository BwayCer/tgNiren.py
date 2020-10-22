#!/usr/bin/env python3


import typing
import asyncio
import utils.novice as novice
from tgkream.tgTool import telethon, TgDefaultInit, TgBaseTool


def run(args: list, _dirpy: str, _dirname: str):
    asyncio.run(asyncRun(args, _dirpy, _dirname))

async def asyncRun(args: list, _dirpy: str, _dirname: str):
    clientBaseCount = int(args[1])
    fromGroupPeer = args[2]
    toGroupPeer = args[3]

    tgTool = TgDefaultInit(
        TgBaseTool,
        clientCount = clientBaseCount,
        papaPhone = novice.py_env['papaPhoneNumber']
    )
    usableClientCount = tgTool.clientCount
    await tgTool.init()

    logNeedle = novice.LogNeedle()
    bandNiUserList = []
    async for info in _iterTuckInfo(tgTool, fromGroupPeer, toGroupPeer):
        myId = info['id']
        client = info['client']
        user = info['user']
        count = info['count']

        if utils.novice.indexOf(bandNiUserList, myId) != -1:
            if len(bandNiUserList) == usableClientCount:
                errMsg = '[tuckUserIntoChannel]: 彷用戶們已盡力'
                logNeedle.push(errMsg)
                raise Exception(errMsg)
            continue

        print('->', myId, user.first_name, user.last_name, user.username, user.id)
        try:
            if count == 1:
                await tgTool.joinGroup(client, toGroupPeer)
            peer = await client.get_input_entity(user.id)
            await client(telethon.functions.channels.InviteToChannelRequest(
                channel = toGroupPeer,
                users = [peer]
            ))
        except telethon.errors.FloodWaitError as err:
            waitTimeSec = err.seconds
            print('-=-')
            print("FloodWaitError: wait {} seconds.".format(waitTimeSec))
            print('-=-')
            maturityDate = utils.novice.dateNowOffset(seconds = waitTimeSec)
            tgTool.chanDataNiUsers.pushBandData(myId, maturityDate)
            bandNiUserList.append(myId)
        except telethon.errors.PeerFloodError as err:
            # 限制發送請求 Too many requests
            print('-=-')
            print('PeerFloodError: {}'.format(type(err), err))
            print('-=-')
            logNeedle.push(
                '[tuckUserIntoChannel]: The +{} phone Get PeerFloodError'.format(myId)
            )
            # TODO 12 小時只是估計值
            maturityDate = utils.novice.dateNowOffset(hours = 12)
            tgTool.chanDataNiUsers.pushBandData(myId, maturityDate)
            bandNiUserList.append(myId)
        except telethon.errors.UserChannelsTooMuchError as err:
            # 用戶已無法再加入新群
            tgTool.chanData.pushGuy(user, err)
        except telethon.errors.UserNotMutualContactError as err:
            # The provided user is not a mutual contact.
            tgTool.chanData.pushGuy(user, err)
        except telethon.errors.UserPrivacyRestrictedError as err:
            # 用戶的隱私設置不允許此行為
            # The user's privacy settings do not allow you to do this. Skipping.
            tgTool.chanData.pushGuy(user, err)
        except Exception as err:
            raise err

async def _bestSingleCount(tgTool: TgBaseTool, groupPeer: str, maxCount: str) -> int:
    client = tgTool.pickClient()['client']
    await tgTool.joinGroup(client, groupPeer)
    _, users = await tgTool.getParticipants(client, groupPeer)
    bestSingleCount = int(len(users) / tgTool.clientCount)
    return bestSingleCount if bestSingleCount < maxCount else 50

async def _getExcludedUserIdList(tgTool: TgBaseTool, groupPeer: str) -> list:
    client = tgTool.pickClient()['client']
    await tgTool.joinGroup(client, groupPeer)
    _, users = await tgTool.getParticipants(client, groupPeer)
    userIds = []
    for user in users:
        userIds.append(user.id)
    return userIds

async def _getPickUserList(
        tgTool: TgBaseTool,
        client: telethon.TelegramClient,
        groupPeer: str,
        offset: int,
        excludedUserList: list,
        amount: int) -> typing.Tuple[int, list]:
    await tgTool.joinGroup(client, groupPeer)
    newOffset, users = await tgTool.getParticipants(
        client = client,
        groupPeer = groupPeer,
        offset = offset,
        excludedUserList = excludedUserList,
        amount = amount
    )
    return (newOffset, users)

async def _iterTuckInfo(
        tgTool: TgBaseTool,
        fromGroupPeer: str,
        toGroupPeer: str) -> dict:
    # TODO 須實現真正意義上的 11 秒
    # 最佳間隔秒數 11~15 可以拉 45~50 人
    # bestIntervalTime = 11
    # 目前以 10 位仿用戶拉人約耗 4 秒
    bestIntervalTime = 20
    bestPullCount = 50
    usableClientCount = tgTool.clientCount
    maxSuccessCount = bestPullCount * usableClientCount
    # 當人數少時平均分配
    bestSingleCount = await _bestSingleCount(tgTool, fromGroupPeer, bestPullCount)
    offsetIndex = 0
    excludedUserList = await _getExcludedUserIdList(tgTool, toGroupPeer)
    # 仿用戶對自己所執行的目標用戶至少需查詢一次
    pickUserInfos = {}

    loopTimes = 0
    async for clientInfo in tgTool.iterPickClient(-1, bestIntervalTime):
        myId = clientInfo['id']
        client = clientInfo['client']

        if myId in pickUserInfos:
            pickUserInfo = pickUserInfos[myId]
            if pickUserInfo['idx'] == -1:
                continue
        else:
            pickUserInfo = pickUserInfos[myId] = {'idx': -1, 'count': 0, 'list': []}

        pickIdx = pickUserInfo['idx']
        pickList = pickUserInfo['list']
        if 0 <= pickIdx and pickIdx < len(pickList):
            print('pickIdx:', pickIdx)
            user = pickList[pickIdx]
            pickCount = pickUserInfo['count'] = pickUserInfo['count'] + 1
            yield {
                'id': myId,
                'client': client,
                'user': user,
                'count': pickCount,
            }

            pickIdx += 1
        else:
            pickIdx = 0
            offsetIndex, pickList = await _getPickUserList(
                tgTool, client, fromGroupPeer,
                offsetIndex, excludedUserList, bestSingleCount
            )
            pickUserInfo['list'] = pickList

            if len(pickList) == 0:
                usableClientCount -= 1
                pickUserInfo['idx'] = -1
                if usableClientCount == 0:
                    print('[_iterTuckInfo]: 名單中已經沒有人了就退出')
                    break
                continue

        pickUserInfo['idx'] = pickIdx

        loopTimes += 1
        if loopTimes == maxSuccessCount:
            break

