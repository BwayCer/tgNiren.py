#!/usr/bin/env python3


import asyncio
import utils.novice as novice
import utils.json
from tgkream.tgTool import telethon, TgDefaultInit, TgBaseTool


def run(args: list, _dirpy: str, _dirname: str):
    asyncio.run(asyncRun(args, _dirpy, _dirname))

async def asyncRun(args: list, _dirpy: str, _dirname: str) -> list:
    groupPeer = args[1]
    jsonFilePath = args[2]

    tgTool = TgDefaultInit(
        TgBaseTool,
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
        # 沒有此用戶或群組名稱
    # except telethon.errors.rpcerrorlist.ChannelPrivateError as err:
        # 此群組可能為私人群組或是你被禁止了
    # except telethon.errors.ChatAdminRequiredError as err:
        # 此行為被要求要有群組管理員權限或者權限不足
    except Exception as err:
        raise err

    utils.json.dump(userIds, jsonFilePath)

