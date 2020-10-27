#!/usr/bin/env python3


import typing
import asyncio
import json
import utils.novice as novice
import webBox.serverMix as serverMix
import webBox.app.utils as appUtils


__all__ = ['subscribe']


_subscriber = []
_prevStatus = {'allCount': 0, 'usableCount': 0}

async def subscribe(pageId: str):
    if novice.indexOf(_subscriber, pageId) == -1:
        _subscriber.append(pageId)

        if len(_subscriber) == 1:
            asyncio.create_task(_latestStatus())

    await _send(pageId, _getNiUsersStatusTxt())

async def _latestStatus():
    while True:
        niUsersStatusInfo = await appUtils.getNiUsersStatusInfo()
        allCount = niUsersStatusInfo['allCount']
        usableCount = niUsersStatusInfo['usableCount']
        isChange = _prevStatus['allCount'] != allCount \
            or _prevStatus['usableCount'] != usableCount

        if isChange:
            _prevStatus['allCount'] = allCount
            _prevStatus['usableCount'] = usableCount

        niUsersStatusTxt = _getNiUsersStatusTxt()
        for pageId in _subscriber:
            if serverMix.wsHouse.connectLength(pageId) == 0:
                pageIdIdx = novice.indexOf(_subscriber, pageId)
                if pageIdIdx != -1:
                    del _subscriber[pageIdIdx]
                break

            if isChange:
                await _send(pageId, niUsersStatusTxt)

        if len(_subscriber) == 0:
            break
        else:
            await asyncio.sleep(3)

def _getNiUsersStatusTxt() -> str:
    return '仿用戶可用比： {}/{}'.format(
        _prevStatus['usableCount'],
        _prevStatus['allCount']
    )

async def _send(pageId: str, niUsersStatusTxt: str):
    innerSession = serverMix.innerSession.get(pageId)
    await serverMix.wsHouse.send(
        pageId,
        json.dumps([{
            'type': 'niUsersStatus.latestStatus',
            'niUsersStatus': niUsersStatusTxt,
            'latestStatus': innerSession['latestStatus']
        }])
    )

