#!/usr/bin/env python3


import os
import sys
import asyncio
import utils.json
import utils.novice as novice
from tgkream.tgTool import TgBaseTool


async def main():
    tgTool = TgBaseTool(
        novice.py_env['apiId'],
        novice.py_env['apiHash'],
        sessionDirPath = novice.py_dirname + '/_tgSession',
        clientCount = 1,
        papaPhone = novice.py_env['papaPhoneNumber']
    )
    await tgTool.init()

    client = await tgTool.pickClient()
    print(await client.get_me())


if __name__ == '__main__':
    asyncio.run(main())
    os._exit(0)

