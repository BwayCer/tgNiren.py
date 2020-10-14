#!/usr/bin/env python3


import typing
import asyncio
import json
import utils.novice as novice
import webBox.serverMix as serverMix
import webBox.app.tgToolUtils as tgToolUtils


def subscribe(pageId: str, prop: typing.Any = None) -> dict:
    if prop == 'latestStatus':
        if novice.indexOf(_latestStatus_subscriber, pageId) == -1:
            _latestStatus_subscriber.append(pageId)

            if len(_latestStatus_subscriber) == 1:
                task = asyncio.create_task(_latestStatus())

        asyncio.create_task(_latestStatus_first(pageId))

        return {'result': True}


_latestStatus_subscriber = []
_latestStatus_prevStatus = {'allCount': 0, 'usableCount': 0}

async def _latestStatus():
    while True:
        niUsersStatusInfo = await tgToolUtils.getNiUsersStatusInfo()
        allCount = niUsersStatusInfo['allCount']
        usableCount = niUsersStatusInfo['usableCount']
        isChange = _latestStatus_prevStatus['allCount'] != allCount \
            or _latestStatus_prevStatus['usableCount'] != usableCount

        if isChange:
            _latestStatus_prevStatus['allCount'] = allCount
            _latestStatus_prevStatus['usableCount'] = usableCount

        niUsersStatusTxt = _latestStatus_getNiUsersStatusTxt()
        for pageId in _latestStatus_subscriber:
            if serverMix.wsHouse.connectLength(pageId) == 0:
                pageIdIdx = novice.indexOf(_latestStatus_subscriber, pageId)
                if pageIdIdx != -1:
                    del _latestStatus_subscriber[pageIdIdx]
                break

            if isChange:
                await _latestStatus_send(pageId, niUsersStatusTxt)

        if len(_latestStatus_subscriber) == 0:
            break
        else:
            await asyncio.sleep(3)

async def _latestStatus_first(pageId: str):
    niUsersStatusTxt = _latestStatus_getNiUsersStatusTxt()
    await _latestStatus_send(pageId, niUsersStatusTxt)

def _latestStatus_getNiUsersStatusTxt() -> str:
    return '仿用戶可用比： {}/{}'.format(
        _latestStatus_prevStatus['usableCount'],
        _latestStatus_prevStatus['allCount']
    )

async def _latestStatus_send(pageId: str, niUsersStatusTxt: str):
    innerSession = serverMix.innerSession.get(pageId)
    await serverMix.wsHouse.send(
        pageId,
        json.dumps([{
            'type': 'niUsersStatus.latestStatus',
            'niUsersStatus': niUsersStatusTxt,
            'latestStatus': innerSession['latestStatus']
        }])
    )

