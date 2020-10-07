#!/usr/bin/env python3


import typing
import asyncio
import json
import utils.novice as novice
import webBox.serverMix as serverMix
from tgkream.tgTool import tgTodoFunc


def subscribe(pageId: str, prop: typing.Any = None) -> dict:
    if prop == 'latestStatus':
        if novice.indexOf(_latestStatus_subscriber, pageId) == -1:
            _latestStatus_subscriber.append(pageId)

            if len(_latestStatus_subscriber) == 1:
                asyncio.ensure_future(_latestStatus())

        return {'result': True}


_latestStatus_subscriber = []
_latestStatus_prevStatus = {'allCount': 0, 'lockCount': 0}

def _latestStatus():
    while True:
        niUsersStatusInfo = tgTodoFunc.getNiUsersStatusInfo()
        allCount =  niUsersStatusInfo['allCount']
        lockCount =  niUsersStatusInfo['lockCount']
        isChange = _latestStatus_prevStatus['allCount'] != allCount \
            or _latestStatus_prevStatus['lockCount'] != lockCount

        niUsersStatusTxt = '仿用戶可用比： {}/{}'.format(lockCount, allCount)
        if isChange:
            _latestStatus_prevStatus['allCount'] = allCount
            _latestStatus_prevStatus['lockCount'] = lockCount

        for pageId in _latestStatus_subscriber:
            if serverMix.wsHouse.connectLength(pageId) == 0:
                pageIdIdx = novice.indexOf(_latestStatus_subscriber, pageId)
                if pageIdIdx != -1:
                    del _latestStatus_subscriber[pageIdIdx]
                break

            if isChange:
                innerSession = serverMix.innerSession.get(pageId)

                await serverMix.wsHouse.send(
                    pageId,
                    json.dumps([{
                        'type': 'niUsersStatus.latestStatus',
                        'niUsersStatus': niUsersStatusTxt,
                        'latestStatus': innerSession['latestStatus']
                    }])
                )

        if len(_latestStatus_subscriber) == 0:
            break
        else:
            await asyncio.sleep(3)

