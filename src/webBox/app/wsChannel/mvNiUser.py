#!/usr/bin/env python3


import typing
import os
import datetime
import re
import utils.chanData
import utils.novice as novice
import webBox.app.utils as appUtils
from webBox.app._wsChannel.niUsersStatus import updateStatus as niUsersStatusUpdateStatus


__all__ = ['mvAll']


_tgAppMainApiId = novice.py_env['tgApp']['main']['apiId']
_sessionDirPath = novice.py_dirname + '/' + novice.py_env['tgSessionDirPath']
_papaPhoneNumber = novice.py_env['papaPhoneNumber']


async def mvAll(pageId: str, wsId: str, prop: typing.Any = None) -> dict:
    chanData = utils.chanData.ChanData()
    niUsers = chanData.getSafe('.niUsers')
    if niUsers != None and len(niUsers['lockList']):
        return {
            'code': 1,
            'message': appUtils.console.logMsg('---', '目前有程式執行中，請稍後在執行。')
        }

    newTgSessionDirPath = os.path.join(
        _sessionDirPath,
        '_' + datetime.datetime.utcnow().strftime('%Y-%m-%dT%H-00-00Z')
    )
    regexAllSessionName = r'^telethon-'
    regexOwnSessionName = r'^telethon-' + str(_tgAppMainApiId) + r'-(\d+).session$'
    moveOwnPhoneCount = 0
    files = os.listdir(_sessionDirPath)
    for fileName in files:
        filePath = os.path.join(_sessionDirPath, fileName)
        if os.path.isfile(filePath):
            isMoveFile = False
            matchTgCode = re.search(regexOwnSessionName, fileName)
            if matchTgCode:
                phoneNumber = matchTgCode.group(1)
                if phoneNumber == _papaPhoneNumber:
                    continue
                moveOwnPhoneCount += 1
                isMoveFile = True
            elif re.search(regexAllSessionName, fileName):
                isMoveFile = True

            if isMoveFile:
                if not os.path.exists(newTgSessionDirPath):
                    os.makedirs(newTgSessionDirPath)

                os.rename(
                    filePath,
                    os.path.join(newTgSessionDirPath, fileName)
                )

    leaveCount = -1 * moveOwnPhoneCount
    await niUsersStatusUpdateStatus(allCount = leaveCount, usableCount = leaveCount)
    niUsers = chanData.getSafe('.niUsers')
    if niUsers != None:
        niUsers['cemetery'].clear()
        niUsers['bandInfos'].clear()
        niUsers['bandList'].clear()
        niUsers['lockList'].clear()
        chanData.store()

    return {
        'code': 1,
        'message': appUtils.console.logMsg('---', '已移除所有仿用戶。')
    }

