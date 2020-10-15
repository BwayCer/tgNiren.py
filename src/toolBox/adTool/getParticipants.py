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

    client = tgTool.pickClient()['client']

    _, isPrivate = telethon.utils.parse_username(groupPeer)
    if isPrivate:
        try:
            await tgTool.joinGroup(client, groupPeer)
        except telethon.errors.UserAlreadyParticipantError as err:
            # 已經是聊天的參與者。 (私有聊天室)
            pass
        except Exception as err:
            errType = type(err)
            if telethon.errors.ChannelsTooMuchError == errType:
                print('您加入了太多的頻道/超級群組。')
            elif telethon.errors.ChannelInvalidError == errType:
                print('無效的頻道對象。')
            elif telethon.errors.ChannelPrivateError == errType:
                print('指定的對象為私人頻道/超級群組。另一個原因可能是您被禁止了。')
            elif telethon.errors.InviteHashEmptyError == errType:
                print('邀請連結丟失。 (私有聊天室)')
            elif telethon.errors.InviteHashExpiredError == errType:
                print('聊天室已過期。 (私有聊天室)')
            elif telethon.errors.InviteHashInvalidError == errType:
                print('無效的邀請連結。 (私有聊天室)')
            elif telethon.errors.SessionPasswordNeededError == errType:
                print('啟用了兩步驗證，並且需要密碼。 (私有聊天室)(登入錯誤?)')
            elif telethon.errors.UsersTooMuchError == errType:
                print('超過了最大用戶數 (ex: 創建聊天)。 (私有聊天室)')
            else:
                print('{} Error: {} (from: {})'.format(
                    errType, err, 'tgTool.joinGroup()'
                ))
            raise err

    try:
        _, users = await tgTool.getParticipants(client, groupPeer)
        userIds = []
        for user in users:
            username = user.username
            if username == None:
                continue
            userIds.append(user.username)
    except Exception as err:
        errType = type(err)
        if telethon.errors.ChannelInvalidError == errType:
            print('無效的頻道對象。')
        elif telethon.errors.ChannelPrivateError == errType:
            print('指定的對象為私人頻道/超級群組。另一個原因可能是您被禁止了。')
        elif telethon.errors.ChatAdminRequiredError == errType:
            print('您沒有執行此操作的權限。')
        elif telethon.errors.InputConstructorInvalidError == errType:
            print('提供的構造函數無效。 (*程式錯誤)')
        elif telethon.errors.TimeoutError == errType:
            print('從工作程序中獲取數據時發生超時。 (*程式錯誤)')
        else:
            print('{} Error: {} (from: {})'.format(
                errType, err, 'tgTool.getParticipants()'
            ))
        raise err

    utils.json.dump(userIds, jsonFilePath)

