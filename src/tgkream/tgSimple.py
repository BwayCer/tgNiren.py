#!/usr/bin/env python3


import typing
import os
import random
import asyncio
import telethon.sync as telethon
import tgkream.errors as errors
import utils.novice as novice
from tgkream.utils import TgTypeing, TgSession


__all__ = ['errors', 'telethon', 'TgTypeing', 'TgSimple']


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
        print('-> login +{}'.format(phoneNumber))
        sessionPath = self.getSessionPath(phoneNumber)

        if not os.path.exists(sessionPath):
            print(errors.errMsg.SessionFileNotExistsTemplate.format(phoneNumber))

        ynLoginContinue = True
        client = TelegramClient(
            self.getSessionPath(phoneNumber, noExt = True),
            self._apiId,
            self._apiHash
        )
        try:
            print('--> client.connect')
            await client.connect()
        except telethon.errors.PhoneNumberBannedError as err:
            ynLoginContinue = False
            print('The phone {} is Banned.'.format(phoneNumber))
            print('please run `rm {}*`'.format(sessionPath))
        except Exception as err:
            print('{} Error: {} '.format(type(err), err))
            raise err

        if ynLoginContinue:
            print('--> client.is_user_authorized')
            if not await client.is_user_authorized():
                print(errors.errMsg.UserNotAuthorizedTemplate.format(phoneNumber))
                print('--> client.send_code_request')
                try:
                    await client.send_code_request(phoneNumber)
                    verifiedCode = input('login {}, Enter the code: '.format(phoneNumber))
                    if verifiedCode == '':
                        return None
                    else:
                        print('--> client.sign_in {} with {} verifiedCode'.format(phoneNumber, verifiedCode))
                        await client.sign_in(phoneNumber, verifiedCode)
                except telethon.errors.rpcerrorlist.PhoneCodeInvalidError as err:
                    print('無效的驗證碼，驗證失敗。')
                    ynLoginContinue = False
                except Exception as err:
                    print('{} Error: {} '.format(type(err), err))
                    raise err

        print('--- login +{} {} ---'.format(
            phoneNumber,
            'success' if ynLoginContinue else 'failed'
        ))
        return client if ynLoginContinue else None

    async def loginPick(self, phoneNumbersTxt: str) -> list:
        print('--- loginPick start ---')
        phoneNumbers = phoneNumbersTxt.split(',')
        clientInfoList = []

        for idx in range(len(phoneNumbers)):
            phoneNumber = phoneNumbers[idx]

            clientInfo = None
            if phoneNumber != '':
                client = await self.login(phoneNumber)
                myInfo = await client.get_me()
                self._clientInfoList.append({
                    'id': myInfo.phone,
                    'userId': myInfo.id,
                    'client': client,
                })
            clientInfoList[idx] = clientInfo

        print('--- loginPick end ---')
        return clientInfoList

    def getRandId(self):
        return random.randrange(1000000, 9999999)

    async def iterLoopInterval(self, length: int, circleInterval: float = 1) -> None:
        prevTimeMs = novice.dateNowTimestamp()
        idxLoop = 0
        while True:
            if circleInterval > 0 and idxLoop != 0:
                nowTimeMs = novice.dateNowTimestamp()
                intervalTimeMs = circleInterval - ((nowTimeMs - prevTimeMs) / 1000)
                if intervalTimeMs > 0:
                    print('wait {} second'.format(intervalTimeMs))
                    await asyncio.sleep(intervalTimeMs)
                    prevTimeMs = novice.dateNowTimestamp()
                else:
                    prevTimeMs = nowTimeMs

            yield idxLoop
            idxLoop += 1
            if 0 < length and length <= idxLoop:
                break

