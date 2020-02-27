#!/usr/bin/env python3


import typing
import asyncio
import json
import webBox.serverMix as serverMix
from tgkream.tgTool import tgTodoFunc


def subscribe(pageId: str, prop: typing.Any = None) -> dict:
    if prop == 'latestStatus':
        asyncio.ensure_future(_latestStatus(pageId))
        return {'result': True}

async def _latestStatus(pageId: str, prop: typing.Any = None) -> dict:
    innerSession = serverMix.innerSession.get(pageId)

    while True:
        niUsersStatusInfo = tgTodoFunc.getNiUsersStatusInfo()
        await serverMix.wsHouse.send(
            pageId,
            json.dumps([{
                'type': 'niUsersStatus.latestStatus',
                'niUsersStatus': '仿用戶可用比： {}/{} ({})'.format(
                    niUsersStatusInfo['lockCount'],
                    niUsersStatusInfo['allCount'],
                    '工具可用' if niUsersStatusInfo['allCount'] - niUsersStatusInfo['lockCount'] > 3 else '工具不可用'
                ),
                'latestStatus': innerSession['latestStatus']
            }])
        )
        await asyncio.sleep(3)

