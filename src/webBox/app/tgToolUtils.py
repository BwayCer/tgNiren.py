#!/usr/bin/env python3


import asyncio
import utils.novice as novice
from tgkream.tgTool import TgDefaultInit, TgBaseTool


__all__ = ['getNiUsersStatusInfo']


_getNiUsersStatusInfo_task = None

async def _getNiUsersStatusInfo_handle():
    tgTool = TgDefaultInit(
        TgBaseTool,
        clientCount = 1,
        papaPhone = novice.py_env['papaPhoneNumber']
    )

    chanDataNiUsers = tgTool.chanDataNiUsers
    usablePhones = chanDataNiUsers.getUsablePhones()
    niUsers = chanDataNiUsers.chanData.data['niUsers']
    bandPhones = niUsers['bandList']
    lockPhones = niUsers['lockList']

    for phoneNumber in usablePhones:
        if novice.indexOf(bandPhones, phoneNumber) != -1 \
                or novice.indexOf(lockPhones, phoneNumber) != -1:
            continue

        client = await tgTool.login(phoneNumber)
        if client != None:
            await tgTool.release(phoneNumber)

    allCount = len(usablePhones)
    lockCount = len(bandPhones) + len(lockPhones)
    return {
        'allCount': allCount,
        'lockCount': lockCount,
        'usableCount': allCount - lockCount,
    }

async def getNiUsersStatusInfo():
    global _getNiUsersStatusInfo_task
    task = _getNiUsersStatusInfo_task
    if task == None or task.done():
        task = _getNiUsersStatusInfo_task \
            = asyncio.create_task(_getNiUsersStatusInfo_handle())

    return await asyncio.wrap_future(task)

