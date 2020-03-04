#!/usr/bin/env python3


import asyncio
import utils.novice as novice
import utils.json
from tgkream.tgTool import telethon, TgBaseTool


def run(args: list, _dirpy: str, _dirname: str):
    asyncio.run(asyncRun(args, _dirpy, _dirname))

async def asyncRun(args: list, _dirpy: str, _dirname: str) -> list:
    groupPeer = args[1]
    jsonFilePath = args[2]

    tgTool = TgBaseTool(
        novice.py_env['apiId'],
        novice.py_env['apiHash'],
        sessionDirPath = _dirname + '/_tgSession',
        clientCount = 1,
        papaPhone = novice.py_env['papaPhoneNumber']
    )
    await tgTool.init()

    try:
        client = await tgTool.pickClient()
        await tgTool.joinGroup(client, groupPeer)
        _, users = await tgTool.getParticipants(client, groupPeer)
        userIds = []
        for user in users:
            username = user.username
            if username == None:
                continue
            userIds.append(user.username)
    # except telethon.errors.ValueError as err:
        # 沒有此群組
    # except telethon.errors.rpcerrorlist.ChannelPrivateError as err:
        # 此群組可能為私人群組或是你被禁止了
    except Exception as err:
        raise err

    utils.json.dump(userIds, jsonFilePath)

