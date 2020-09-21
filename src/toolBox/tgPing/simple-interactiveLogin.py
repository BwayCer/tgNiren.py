#!/usr/bin/env python3


import asyncio
from tgkream.tgSimple import TgDefaultInit, TgSimple


def run(args: list, _dirpy: str, _dirname: str):
    asyncio.run(asyncRun(args, _dirpy, _dirname))

async def asyncRun(args: list, _dirpy: str, _dirname: str) -> list:
    if len(args) < 2:
        raise ValueError('Usage: <phoneNumber>')

    phoneNumber = args[1]

    tgTool = TgDefaultInit(TgSimple)
    client = await tgTool.login(phoneNumber)

    if client != None:
        print(await client.get_me())

