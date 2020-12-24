#!/usr/bin/env python3

import os
import random
import asyncio
import utils.novice as novice
from tgkream.tgSimple import telethon, TgDefaultInit, TgSimple


def run(args: list, _dirpy: str, _dirname: str):
    asyncio.run(asyncRun(args, _dirpy, _dirname))

async def asyncRun(args: list, _dirpy: str, _dirname: str) -> list:
    if len(args) < 2:
        raise ValueError('Usage: <phoneNumber>')

    phoneNumber = args[1]

    tgTool = TgDefaultInit(TgSimple)
    client = await tgTool.login(phoneNumber)

    if client == None:
        return
        print(await client.get_me())

    #update photo>>
    #direct = novice.py_dirname + '/photos/photo1.jpg'
    _photoPath = novice.py_dirname + '/' + novice.py_env['modemPool']['photoPath']
    files = os.listdir(_photoPath)
    file_number = len(files) - 1
    indexStart = random.randrange(0, file_number)
    direct = _photoPath + '/' + files[indexStart]
    await client(telethon.functions.photos.UploadProfilePhotoRequest(
        await client.upload_file(direct)
    ))
    #update photo<<

