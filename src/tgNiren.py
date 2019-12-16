#!/usr/bin/env python3


import os
import sys
import asyncio
import utils.json
import utils.novice
from tgkream.tgTool import TgNiUsers


_dirname = os.path.dirname(os.path.abspath(sys.argv[0]))
_env = utils.json.loadYml(_dirname + '/env.yml')


async def main():
    tgTool = TgNiUsers(
        _env['apiId'],
        _env['apiHash'],
        sessionDirPath = _dirname + '/_tgSession',
        clientCountLimit = 1,
        papaPhone = _env['papaPhoneNumber']
    )
    await tgTool.init()

    client = await tgTool.pickClient()
    print(await client.get_me())


if __name__ == '__main__':
    asyncio.run(main())
    os._exit(0)

