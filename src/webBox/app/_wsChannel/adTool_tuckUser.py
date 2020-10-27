#!/usr/bin/env python3


import typing
import random
import asyncio
import json
import utils.novice as novice
import webBox.serverMix as serverMix
from tgkream.tgTool import knownError, telethon, TgDefaultInit, TgBaseTool
import webBox.app.utils as appUtils
from webBox.app._wsChannel.niUsersStatus import updateStatus as niUsersStatusUpdateStatus


__all__ = ['tuckUser']


async def tuckUser(pageId: str, prop: typing.Any = None) -> dict:
    innerSession = serverMix.innerSession.get(pageId)
    if innerSession['runing']:
        return {
            'code': -1,
            'message': '工具執行中。',
        }

    if type(prop) != dict:
        return {
            'code': -1,
            'message': '"prop" 參數必須是 `Object` 類型。',
        }
    if not ('userPeerList' in prop and type(prop['userPeerList']) == list):
        return {
            'code': -1,
            'message': '"prop.userPeerList" 參數不符合預期',
        }
    if not ('toGroupPeer' in prop and type(prop['toGroupPeer']) == str):
        return {
            'code': -1,
            'message': '"prop.toGroupPeer" 參數不符合預期',
        }

    innerSession['runing'] = True
    asyncio.create_task(_tuckUserAction(pageId, innerSession, prop))
    return {
        'code': 0,
        'message': '請求已接收。'
    }

async def _tuckUserAction(pageId: str, innerSession: dict, data: dict):
    try:
        niUsersStatusInfo = await appUtils.getNiUsersStatusInfo()
        allNiUsersCount = niUsersStatusInfo['allCount']
        usableNiUsersCount = int(niUsersStatusInfo['usableCount'] * 8 / 10)
        if usableNiUsersCount < 1:
            await _tuckUserAction_send(pageId, -1, '工具目前無法使用。')
            return

        userPeers = data['userPeerList']
        toGroupPeer = data['toGroupPeer']

        # usedClientCount = int(len(userPeers) / 50) + 1
        # usedClientCount = usedClientCount \
            # if usedClientCount < usableNiUsersCount else usableNiUsersCount
        usedClientCount = len(userPeers)
        usedClientCount = usedClientCount \
            if usedClientCount < usableNiUsersCount else usableNiUsersCount

        # 用於打印日誌
        runId = str(random.randrange(1000000, 9999999))
        await _tuckUserAction_send(
            pageId, 1,
            appUtils.console.log(
                runId, _interactiveMessage, 'tuckUserInit', usedClientCount
            )
        )
        try:
            tgTool = appUtils.getTgTool(usedClientCount)
            await tgTool.init()
        except Exception as err:
            innerSession['runing'] = False
            await _tuckUserAction_send(
                pageId, -1,
                appUtils.console.log(runId, _interactiveMessage, 'tuckUserInitFailed'),
                isError = True
            )
            return

        await niUsersStatusUpdateStatus(usableCount = -1 * usedClientCount)

        finalPeers = _filterGuy(tgTool, userPeers)
        finalPeersLength = len(finalPeers)
        pickNiUserList = []
        bandNiUserList = []
        idx = 0
        async for clientInfo in tgTool.iterPickClient(-1, 11):
            myId = clientInfo['id']
            client = clientInfo['client']

            if novice.indexOf(bandNiUserList, myId) != -1:
                if len(bandNiUserList) == usedClientCount:
                    break
                continue

            readableIdx = idx + 1
            userPeer = finalPeers[idx]

            appUtils.console.log(
                runId, _interactiveMessage, 'tuckUserProcess',
                readableIdx, finalPeersLength,
                ' use {} for {} -> {}'.format(myId, userPeer, toGroupPeer)
            )
            await _tuckUserAction_send(
                pageId, 1,
                appUtils.console.getMsg(
                    _interactiveMessage, 'tuckUserProcess',
                    readableIdx, finalPeersLength, ''
                )
            )

            if novice.indexOf(pickNiUserList, myId) == -1:
                await _tuckUserAction_send(
                    pageId, 1,
                    appUtils.console.log(
                        runId, _interactiveMessage, 'tuckUserProcessNiUserJoin',
                        readableIdx, finalPeersLength
                    )
                )
                try:
                    await tgTool.joinGroup(client, toGroupPeer)
                    pickNiUserList.append(myId)
                except telethon.errors.UserAlreadyParticipantError as err:
                    # 已經是聊天的參與者。 (私有聊天室)
                    pass
                # except telethon.errors.ChannelsTooMuchError as err:
                    # 已加入了太多的渠道/超級群組。
                    # 這樣的仿用戶是否該封鎖了 ?
                    # novice.logNeedle.push(
                        # '(runId: {}) {} get ChannelsTooMuchError: wait 30 day.'.format(
                            # runId, myId
                        # )
                    # )
                    # maturityDate = novice.dateNowOffset(days = 30)
                    # tgTool.chanDataNiUsers.pushBandData(myId, maturityDate)
                    # bandNiUserList.append(myId)
                except Exception as err:
                    bandNiUserList.append(myId)

                    errMsg = ''
                    isTraceError = False

                    if knownError.has('joinGroupMethod', err):
                        errMsg = knownError.getMsg('joinGroupMethod', err)
                        appUtils.console.catchErrorMsg(runId, 'joinGroupMethod', errMsg)
                    else:
                        errMsg = appUtils.console.catchError(runId, 'joinGroupMethod')
                        isTraceError = True

                    await _tuckUserAction_send(
                        pageId, -2, errMsg, isError = isTraceError
                    )

                    continue

            await _tuckUserAction_send(
                pageId, 1,
                appUtils.console.log(
                    runId, _interactiveMessage, 'tuckUserProcessTuck',
                    readableIdx, finalPeersLength
                )
            )

            _, isPrivate = telethon.utils.parse_username(toGroupPeer)
            realToGroupPeer = toGroupPeer \
                if not isPrivate else await client.get_entity(toGroupPeer)

            try:
                await client(telethon.functions.channels.InviteToChannelRequest(
                    channel = realToGroupPeer,
                    users = [userPeer]
                ))
            except telethon.errors.FloodWaitError as err:
                waitTimeSec = err.seconds
                if waitTimeSec < 180:
                    await _tuckUserAction_send(
                        pageId, 1,
                        appUtils.console.catchError(
                            runId, 'InviteToChannelRequest',
                            appUtils.console.baseMsg, 'commonErrors_floodWait',
                            waitTimeSec
                        )
                    )
                    await asyncio.sleep(waitTimeSec)
                else:
                    appUtils.console.catchError(
                        runId, 'InviteToChannelRequest',
                        appUtils.console.baseMsg, 'commonErrors_FloodWaitError',
                        myId, waitTimeSec
                    )
                    maturityDate = novice.dateNowOffset(seconds = waitTimeSec)
                    tgTool.chanDataNiUsers.pushBandData(myId, maturityDate)
                    bandNiUserList.append(myId)

                continue
            except telethon.errors.PeerFloodError as err:
                # 限制發送請求 Too many requests
                appUtils.console.catchError(
                    runId, 'InviteToChannelRequest',
                    appUtils.console.baseMsg, 'commonErrors_PeerFloodError',
                    myId
                )
                # TODO 12 小時只是估計值
                maturityDate = novice.dateNowOffset(hours = 12)
                tgTool.chanDataNiUsers.pushBandData(myId, maturityDate)
                bandNiUserList.append(myId)

                continue
            except Exception as err:
                errTypeName = err.__class__.__name__
                errMsg = ''
                isTraceError = False

                if knownError.has('InviteToChannelRequest', err):
                    errMsg = knownError.getMsg('InviteToChannelRequest', err)
                    appUtils.console.catchErrorMsg(
                        runId, 'InviteToChannelRequest', errMsg
                    )

                    if novice.indexOf(niUserBlockedError, errTypeName) != -1:
                        bandNiUserList.append(myId)
                else:
                    errMsg = appUtils.console.catchError(runId, 'InviteToChannelRequest')
                    isTraceError = True
                    bandNiUserList.append(myId)

                await _tuckUserAction_send(pageId, -2, errMsg, isError = isTraceError)

            idx += 1
            if idx == finalPeersLength:
                break

        if len(bandNiUserList) < usedClientCount:
            await _tuckUserAction_send(
                pageId, 1,
                appUtils.console.log(runId, _interactiveMessage, 'tuckUserEnd')
            )
        else:
            await _tuckUserAction_send(
                pageId, -2,
                appUtils.console.error(
                    runId, _interactiveMessage, 'tuckUserUserExhausted',
                    readableIdx, finalPeersLength
                )
            )
    except Exception as err:
        await _tuckUserAction_send(
            pageId, -1,
            appUtils.console.catchError(runId, 'TuckUserAction'),
            isError = True
        )
    finally:
        appUtils.console.logMsg(runId, 'tgTool.release()'),
        innerSession['runing'] = False
        if 'tgTool' in locals():
            await tgTool.release()
            await niUsersStatusUpdateStatus(usableCount = usedClientCount)


_interactiveMessage = {
    # -2 互動錯誤
    'tuckUserUserExhausted': '進度： {}/{} (仿用戶用盡)',
    # -1 程式錯誤
    'tuckUserInitFailed': '拉人入群初始化... (失敗)',
    # 1 普通互動
    'tuckUserInit': '拉人入群初始化... ({} 位仿用戶響應)',
    'tuckUserProcess': '進度： {}/{}{}',
    'tuckUserProcessNiUserJoin': '進度： {}/{} - 仿用戶加入頻道/群組',
    'tuckUserProcessTuck': '進度： {}/{} - 拉人入群',
    'tuckUserEnd': '拉人入群結束',
}

niUserBlockedError = [
    'UserBannedInChannelError',
]

async def _tuckUserAction_send(
        pageId: str,
        code: int,
        message: str,
        isError = False) -> None:
    payload = {
        'type': 'adTool.tuckUserAction',
        'code': code,
        'message': message,
    }
    if isError:
        errInfo = novice.sysExceptionInfo()
        errMsg = novice.sysTracebackException()
        payload['message'] += '\n' + errMsg
        payload['catchError'] = {
            'name': errInfo['name'],
            'message': errInfo['message'],
            'stackList': errInfo['stackList'],
        }
    await serverMix.wsHouse.send(
        pageId,
        json.dumps([payload])
    )

def _filterGuy(tgTool: TgBaseTool, mainList: typing.List[str]) -> typing.List[str]:
    blackGuyList = tgTool.chanData.data['blackGuy']['list']
    newList = []
    for peer in mainList:
        if novice.indexOf(blackGuyList, peer) == -1:
            newList.append(peer)
    return newList

