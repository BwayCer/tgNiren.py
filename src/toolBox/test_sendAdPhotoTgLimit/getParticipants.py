#!/usr/bin/env python3


import os
import asyncio
import utils.json
from tgkream.tgTool import TgBaseTool, telethon, TelegramClient


def run(args: list, _dirpy: str, _dirname: str):
    asyncio.run(asyncRun(args, _dirpy, _dirname))

async def asyncRun(args: list, _dirpy: str, _dirname: str) -> list:
    groupPeer = args[1]

    _env = utils.json.loadYml(_dirname + '/env.yml')

    tgTool = TgBaseTool(
        _env['apiId'],
        _env['apiHash'],
        sessionDirPath = _dirname + '/_tgSession',
        clientCount = 1,
        papaPhone = _env['papaPhoneNumber']
    )
    await tgTool.init()

    sendUsersFilePath = os.path.join(_dirpy, 'sendUsers.json')
    if os.path.exists(sendUsersFilePath):
        groupUsers = utils.json.load(sendUsersFilePath)
    else:
        groupUsers = []

    try:
        client = await tgTool.pickClient()
        await tgTool.joinGroup(client, groupPeer)
        _, users = await tgTool.getParticipants(client, groupPeer)
        countGetUser = 0
        for user in users:
            username = user.username
            if username != None:
                countGetUser += 1
                groupUsers.append(user.username)
    except ValueError as err:
        print('沒有此用戶或群組名稱')
        raise err
    except telethon.errors.ChatAdminRequiredError as err:
        print('此行為被要求要有群組管理員權限或者權限不足')
        raise err
    except telethon.errors.ChannelPrivateError as err:
        print('此群組可能為私人群組或是你被禁止了')
        raise err
    except Exception as err:
        raise err

    print('此次增加 {} 個用戶。'.format(countGetUser))
    utils.json.dump(groupUsers, sendUsersFilePath)

