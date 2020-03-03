#!/usr/bin/env python3


import typing
import random
import asyncio
import json
import utils.novice as novice
import webBox.serverMix as serverMix


def pin(pageId: str, prop: typing.Any = None) -> dict:
    times = 9 if type(prop) != int else prop
    idInt = random.randrange(1000000, 9999999)
    asyncio.ensure_future(pon(pageId, idInt, times))
    return {'result': 'pon-{}-ok'.format(idInt)}

async def pon(pageId: str, idInt: int, times: int) -> None:
    for idx in range(times):
        await asyncio.sleep(7)
        await serverMix.wsHouse.send(
            pageId,
            json.dumps([{
                'type': 'pinpon.pon',
                'result': 'pon-{}-{}'.format(idInt, idx),
            }])
        )

