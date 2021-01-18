#!/usr/bin/env python3


import typing
import random
import asyncio
import utils.novice as novice
import webBox.serverMix as serverMix


def pin(pageId: str, wsId: str, prop: typing.Any = None) -> dict:
    times = 9 if type(prop) != int else prop
    idInt = random.randrange(1000000, 9999999)
    asyncio.ensure_future(pon(pageId, idInt, times))
    return f'pon-{idInt}-ok'

async def pon(pageId: str, idInt: int, times: int) -> None:
    for idx in range(times):
        await asyncio.sleep(7)
        await serverMix.wsHouse.send(
            pageId,
            fnResult = {
                'name': 'pinpon.pon',
                'result': f'pon-{idInt}-{idx}',
            }
        )

