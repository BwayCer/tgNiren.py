#!/usr/bin/env python3


import typing
import os
import datetime
import asyncio
import json
import utils.novice as novice
import webBox.serverMix as serverMix
from tgkream.tgTool import TgBaseTool, telethon, tgTodoFunc


__all__ = ['paperSlip']


def paperSlip(pageId: str, prop: typing.Any = None) -> dict:
    innerSession = serverMix.innerSession.get(pageId)
    niUsersStatusInfo = tgTodoFunc.getNiUsersStatusInfo()
    if innerSession['runing']:
        return {
            'code': -1,
            'message': '工具執行中。',
        }
    elif niUsersStatusInfo['allCount'] - niUsersStatusInfo['lockCount'] < 3:
        return {
            'code': -1,
            'message': '工具目前無法使用。',
        }


    if type(prop) != dict:
        return {
            'code': -1,
            'message': '"prop" 參數必須是 `Object` 類型。',
        }
    if not ( \
            'forwardPeerList' in prop \
            and type(prop['forwardPeerList']) == list):
        return {
            'code': -1,
            'message': '"prop.forwardPeerList" 參數不符合預期',
        }
    if not ( \
            'mainGroup' in prop \
            and type(prop['mainGroup']) == str):
        return {
            'code': -1,
            'message': '"prop.mainGroup" 參數不符合預期',
        }
    if not ( \
            'messageId' in prop \
            and type(prop['messageId']) == int):
        return {
            'code': -1,
            'message': '"prop.messageId" 參數不符合預期',
        }

    innerSession['runing'] = True
    asyncio.ensure_future(_paperSlipAction(pageId, innerSession, prop))
    return {
        'code': 0,
        'message': '請求已接收。'
    }

async def _paperSlipAction(pageId: str, innerSession: dict, data: dict):
    forwardPeers = data['forwardPeerList']
    mainGroup = data['mainGroup']
    messageId = data['messageId']

    usedClientCount = 3
    latestStatus = ''
    try:
        latestStatus = '炸群進度： 初始化...'
        await _paperSlipAction_send(pageId, 1, latestStatus)
        tgTool = TgBaseTool(
            novice.py_env['apiId'],
            novice.py_env['apiHash'],
            sessionDirPath = novice.py_dirname + '/' + novice.py_env['tgSessionDirPath'],
            clientCount = usedClientCount,
            papaPhone = novice.py_env['papaPhoneNumber']
        )
        await tgTool.init()
    except Exception as err:
        innerSession['runing'] = False
        latestStatus += ' (失敗)'
        await _paperSlipAction_send(pageId, -1, latestStatus, ynError = True)
        return

    try:
        # 用於打印日誌
        runId = tgTool.getRandId()
        finalPeers = _filterGuy(tgTool, forwardPeers)
        finalPeersLength = len(finalPeers)
        bandNiUserList = []
        idx = 0
        # TODO 越來越容易被封 但至少也能傳近乎 200 則 所以暫且不先延長時間
        async for clientInfo in tgTool.iterPickClient(-1, 1, whichNiUsers = True):
            myId = clientInfo['id']
            client = clientInfo['client']

            if novice.indexOf(bandNiUserList, myId) != -1:
                if len(bandNiUserList) == usedClientCount:
                    break
                continue

            if finalPeersLength <= idx:
                break

            forwardPeer = finalPeers[idx]
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
                latestStatus = '炸群進度： {}/{}'.format(idx, finalPeersLength)
                await _paperSlipAction_send(pageId, 1, latestStatus)
                print('(runId: {}) ok: {}/{}'.format(runId, idx, finalPeersLength))
            except telethon.errors.MessageIdInvalidError as err:
                print('(runId: {}) {} get MessageIdInvalidError: {}'.format(
                    runId, myId, err
                ))
                raise err
            except telethon.errors.FloodWaitError as err:
                waitTimeSec = err.seconds
                print('(runId: {}) {} get FloodWaitError: wait {} seconds.'.format(runId, myId, waitTimeSec))
                # TODO 秒數待驗證
                if waitTimeSec < 180:
                    await asyncio.sleep(waitTimeSec)
                else:
                    maturityDate = novice.dateNowAfter(seconds = waitTimeSec)
                    tgTool.chanDataNiUsers.pushBandData(myId, maturityDate)
                    bandNiUserList.append(myId)
            except telethon.errors.PeerFloodError as err:
                # 限制發送請求 Too many requests
                print('(runId: {}) {} get PeerFloodError: wait 1 hour.'.format(runId, myId))
                # TODO 12 小時只是估計值
                maturityDate = novice.dateNowAfter(hours = 12)
                tgTool.chanDataNiUsers.pushBandData(myId, maturityDate)
                bandNiUserList.append(myId)
            except telethon.errors.ChatWriteForbiddenError as err:
                # You can't write in this chat
                print('(runId: {}) {} get ChatWriteForbiddenError: {}'.format(runId, myId, err))
                tgTool.chanData.pushGuy(
                    await client.get_entity(forwardPeer),
                    err
                )
                idx += 1
            except Exception as err:
                print('(runId: {}) {} get {} Error: {} (target group: {})'.format(
                    runId, myId, type(err), err, forwardPeer
                ))
                # 預防性處理，避免相同錯誤一值迴圈
                bandNiUserList.append(myId)

        latestStatus += ' ({})'.format(
            '仿用戶用盡' if len(bandNiUserList) == usedClientCount else '結束'
        )
        await _paperSlipAction_send(pageId, 1, latestStatus)
    except Exception as err:
        latestStatus += ' (失敗)'
        await _paperSlipAction_send(pageId, -1, latestStatus, ynError = True)
    finally:
        innerSession['runing'] = False
        await tgTool.release()

async def _paperSlipAction_send(
        pageId: str,
        code: int,
        message: str,
        ynError = False) -> None:
    payload = {
        'type': 'adTool.paperSlipAction',
        'code': code,
        'message': message,
    }
    if ynError:
        errInfo = novice.sysExceptionInfo()
        errMsg = novice.sysTracebackException()
        payload['message'] += '\n{}'.format(errMsg)
        payload['error'] = {
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

