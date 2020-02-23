#!/usr/bin/env python3


import typing
import os
import re
import telethon.sync as telethon


class TgTypeing():
    Peer = typing.Union[
        telethon.types.Chat,
        telethon.types.User,
        telethon.types.Channel,
    ]
    InputPeer = typing.Union[
        telethon.types.InputPeerEmpty,
        telethon.types.InputPeerSelf,
        telethon.types.InputPeerChat,
        telethon.types.InputPeerUser,
        telethon.types.InputPeerChannel,
        telethon.types.InputPeerUserFromMessage,
        telethon.types.InputPeerChannelFromMessage,
    ]
    # Telethon 的 "peer" 欄位能自動判斷 (調用 `get_input_entity()` 方法)
    AutoInputPeer = typing.Union[str, InputPeer]


class TgSession():
    def __init__(self, sessionDirPath: str = ''):
        self._sessionDirPath = sessionDirPath
        if not os.path.exists(sessionDirPath):
            os.makedirs(sessionDirPath)

    _regexSessionName = r'^telethon-(\d+).session$'

    def getOwnPhones(self) -> list:
        phones = []
        files = os.listdir(self._sessionDirPath)
        for fileName in files:
            if os.path.isfile(os.path.join(self._sessionDirPath, fileName)):
                matchTgCode = re.search(self._regexSessionName, fileName)
                if matchTgCode:
                    phoneNumber = matchTgCode.group(1)
                    phones.append(phoneNumber)
        return phones

    def getSessionPath(self, phoneNumber: str, noExt: bool = False):
        path = self._sessionDirPath + '/telethon-' + phoneNumber
        if noExt == False:
            path += '.session'
        return path

