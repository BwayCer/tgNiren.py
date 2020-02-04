#!/usr/bin/env python3


import typing
import os
import telethon.sync as telethon
import tgkream.errors as errors
from tgkream.utils import TgTypeing, TgSession


__all__ = ['errors', 'TgTypeing', 'TgSimple']


TelegramClient = telethon.TelegramClient


class TgSimple(TgSession):
    def __init__(self,
            apiId: str,
            apiHash: str,
            sessionDirPath: str,
            papaPhone: str = 0):
        TgSession.__init__(self, sessionDirPath)

        self._apiId = apiId
        self._apiHash = apiHash

    # if phoneNumber == '+8869xxx', input '8869xxx' (str)
    async def login(self, phoneNumber: str) -> typing.Union[None, TelegramClient]:
        sessionPath = self.getSessionPath(phoneNumber)

        if not os.path.exists(sessionPath):
            raise errors.UserNotAuthorized(
                errors.errMsg.SessionFileNotExistsTemplate.format(phoneNumber)
            )

        client = TelegramClient(
            self.getSessionPath(phoneNumber, noExt = True),
            self._apiId,
            self._apiHash
        )
        try:
            await client.connect()
        # except tele.errors.PhoneNumberBannedError as err:
            # print('rm telethon-{}.*'.format(phoneNumber))
        except Exception as err:
            print('{} Error: {}', type(err), err)
            raise err

        if not await client.is_user_authorized():
            raise errors.UserNotAuthorized(
                errors.errMsg.UserNotAuthorizedTemplate.format(phoneNumber)
            )

        return client

