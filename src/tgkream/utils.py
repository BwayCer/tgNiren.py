#!/usr/bin/env python3


import typing
import os
import re
import telethon.sync as telethon
import utils.novice as novice


__all__ = ['TgTypeing', 'TgSession', 'TgDefaultInit']


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
    def __init__(self, prifix: str = 'NoPrifix'):
        self._sessionDirPath = novice.py_dirname + '/' + novice.py_env['tgSessionDirPath']
        self._sessionPrifix = prifix
        self._regexSessionName = r'^' + prifix + r'-(\d+).session$'

        if not os.path.exists(self._sessionDirPath):
            os.makedirs(self._sessionDirPath)

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
        return '{}/{}-{}{}'.format(
            self._sessionDirPath,
            self._sessionPrifix,
            phoneNumber,
            '' if noExt else '.session'
        )


def TgDefaultInit(TgClass, *args, **kwargs):
    apiId = novice.py_env['apiId']
    return TgClass(
        apiId,
        novice.py_env['apiHash'],
        sessionPrifix = 'telethon-' + apiId,
        *args, **kwargs
    )

