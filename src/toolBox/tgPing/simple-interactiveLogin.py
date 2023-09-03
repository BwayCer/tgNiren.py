#!/usr/bin/env python3


import sys
import os
import asyncio
from tgkream.tgSimple import TgDefaultInit, TgSimple


def run(args: list, _dirpy: str, _dirname: str):
    asyncio.run(asyncRun(args, _dirpy, _dirname))

async def asyncRun(args: list, _dirpy: str, _dirname: str) -> list:
    if len(args) < 2:
        raise ValueError('Usage: <phoneNumber>')

    # NOTE:
    # 電話號碼以文字或數字類型表示，或有無 "+" 符號 Telethon 都接受，
    # 不過統一使用不含 "+" 的文字表示。 (ex: '8869xxx')
    phoneNumber = args[1]

    tgTool = TgDefaultInit(TgSimple)
    client = await tgTool.login(phoneNumber)

    if client != None:
        print(await client.get_me())

