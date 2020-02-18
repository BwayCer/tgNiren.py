#!/usr/bin/env python3


import asyncio
import utils.json
from tgkream.tgSimple import TgSimple


def run(args: list, _dirpy: str, _dirname: str):
    asyncio.run(asyncRun(args, _dirpy, _dirname))

async def asyncRun(args: list, _dirpy: str, _dirname: str) -> list:
    if len(args) < 2:
        raise ValueError('Usage: <phoneNumber>')

    phoneNumber = args[1]

    _env = utils.json.loadYml(_dirname + '/env.yml')

    tgTool = TgSimple(
        _env['apiId'],
        _env['apiHash'],
        sessionDirPath = _dirname + '/' + _env['tgSessionDirPath'],
    )
    client = await tgTool.login(phoneNumber)

    if client == None:
        raise Exception('Failed Login')
    else:
        print(await client.get_me())

