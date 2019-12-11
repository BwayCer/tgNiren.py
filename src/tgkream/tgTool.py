#!/usr/bin/env python3


import typing
import os
import datetime
import random
import re
import asyncio
import contextlib
import telethon.sync as telethon
import utils.chanData
import utils.novice
import tgkream.errors as errors


__all__ = ['TgNiUsers']


TelegramClient = telethon.TelegramClient


class _NiUsersPhoneChoose():
    def __init__(self, sessionDirPath: str = '', papaPhone: str = 0):
        self._sessionDirPath = sessionDirPath
        if not os.path.exists(sessionDirPath):
            os.makedirs(sessionDirPath)

        self._chanData = utils.chanData.ChanData()
        if self._chanData.getSafe('.niUsers') == None:
            self._chanData.set('.niUsers', {
                'cemetery': [],
                'bandInfos': [],
                'bandList': [],
                'lockList': [],
            })
        else:
            self.updateBandInfo()

        self._papaPhone = papaPhone
        self.pickPhones = []

    @utils.chanData.ChanData.dFakeLockSet(memberPath = '.niUsers', ysStore = True)
    def updateBandInfo(self) -> dict:
        niUsers = self._chanData.get('.niUsers')

        bandInfos = niUsers['bandInfos']
        bandInfosLength = len(bandInfos)
        if bandInfosLength == 0:
            return niUsers

        bands = niUsers['bandList']
        nowTimeMs = utils.novice.dateTimestamp(datetime.datetime.now())
        for idx in range(bandInfosLength):
            bandInfo = bandInfos[idx]
            if bandInfo['bannedWaitTimeMs'] < nowTimeMs:
                del bandInfos[idx]
                bands.remove(bandInfo['id'])

        return niUsers

    _regexSessionName = r'^telethon-(\d+).session$'

    def _getUsablePhones(self) -> list:
        phones = []
        files = os.listdir(self._sessionDirPath)
        for fileName in files:
            if os.path.isfile(os.path.join(self._sessionDirPath, fileName)):
                matchTgCode = re.search(self._regexSessionName, fileName)
                if matchTgCode:
                    phoneNumber = matchTgCode.group(1)
                    if phoneNumber != self._papaPhone:
                        phones.append(phoneNumber)
        return phones

    def getSessionPath(self, phoneNumber: str, noExt: bool = False):
        path = self._sessionDirPath + '/telethon-' + phoneNumber
        if noExt == False:
            path += '.session'
        return path

    @utils.chanData.ChanData.dFakeLockSet(memberPath = '.niUsers', ysStore = True)
    def _pushCemeteryData_chanData(self, phoneNumber: str) -> list:
        niUsers = self._chanData.get('.niUsers')

        locks = niUsers['lockList']
        locksIdx = utils.novice.indexOf(locks, phoneNumber)
        if locksIdx != -1:
            del locks[locksIdx]

        bands = niUsers['bandList']
        bandsIdx = utils.novice.indexOf(bands, phoneNumber)
        if bandsIdx != -1:
            del bands[bandsIdx]
            bandInfos = niUsers['bandInfos']
            bandInfosLength = len(bandInfos)
            for bandInfosIdx in range(bandInfosLength):
                bandInfo = bandInfos[bandInfosIdx]
                if bandInfo['id'] == phoneNumber:
                    del bandInfos[bandInfosIdx]
                    break

        return niUsers

    def pushCemeteryData(self, phoneNumber: str, err: Exception) -> bool:
        sessionPath = self.getSessionPath(phoneNumber)
        if not os.path.exists(sessionPath):
            os.remove(sessionPath)
            self._pushCemeteryData_chanData(phoneNumber)
            return self._chanData.opt('jsonarrappend', '.niUsers.cemetery', {
                'id': phoneNumber,
                'message': '{} error: {}'.format(type(err), err),
            })
        return False

    def pushBandData(self, phoneNumber: str, dt: datetime.datetime) -> bool:
        bands = self._chanData.get('.niUsers.bandList')
        if utils.novice.indexOf(bands, phoneNumber) == -1:
            self._chanData.opt('jsonarrappend', '.niUsers.bandList', phoneNumber)
            return self._chanData.opt('jsonarrappend', '.niUsers.bandInfos', {
                'id': phoneNumber,
                'bannedWaitDate': utils.novice.dateStringify(dt),
                'bannedWaitTimeMs': utils.novice.dateTimestamp(dt)
            })
        return False

    @utils.chanData.ChanData.dFakeLockSet(memberPath = '.niUsers.lockList', maxTimes = 1)
    def _lockPhone_chanData(self, lockList: list) -> list:
        return lockList

    def lockPhone(self, phoneNumber: str) -> bool:
        locks = self._chanData.get('.niUsers.lockList')
        if utils.novice.indexOf(locks, phoneNumber) == -1:
            locks.append(phoneNumber)
            if self._lockPhone_chanData(locks):
                self.pickPhones.append(phoneNumber)
                return True
        return False

    async def pickPhone(self) -> str:
        phones = self._getUsablePhones()
        phonesLength = len(phones)
        # 避免頻繁使用同一帳號
        times = random.randrange(0, phonesLength)
        while True:
            times += 1
            phoneNumber = phones[times % phonesLength]

            niUsers = self._chanData.get('.niUsers')
            bands = niUsers['bandList']
            locks = niUsers['lockList']

            if utils.novice.indexOf(bands, phoneNumber) != -1 \
                    or utils.novice.indexOf(locks, phoneNumber) != -1:
                continue

            if self.lockPhone(phoneNumber):
                return phoneNumber

            await asyncio.sleep(1)

    @utils.chanData.ChanData.dFakeLockSet(memberPath = '.niUsers.lockList')
    def _releaseLockPhone_chanData(self, lockPhoneList: list) -> list:
        locks = self._chanData.get('.niUsers.lockList')
        for phoneNumber in lockPhoneList:
            phoneIdx = utils.novice.indexOf(locks, phoneNumber)
            if phoneIdx != -1:
                del locks[phoneIdx]
        return locks

    def releaseLockPhone(self, phoneNumber: str = ''):
        pickPhones = self.pickPhones
        if phoneNumber == '':
            self._releaseLockPhone_chanData(pickPhones)
            pickPhones.clear()
        else:
            self._releaseLockPhone_chanData([phoneNumber])
            phoneIdx = utils.novice.indexOf(pickPhones, phoneNumber)
            if phoneIdx != -1:
                del pickPhones[phoneIdx]
        self._chanData.store()

class TgNiUsers():
    def __init__(self,
            apiId: str,
            apiHash: str,
            sessionDirPath: str,
            clientCountLimit: int = 0,
            papaPhone: str = 0):
        self._apiId = apiId
        self._apiHash = apiHash
        self._clientCountLimit = clientCountLimit if clientCountLimit > 0 else 3
        self._pickClientIdx = 0
        self._clientInfoList = []

        self.niUsersPhoneChoose = _NiUsersPhoneChoose(sessionDirPath, papaPhone)
        # TODO
        # 處理仿用戶不足問題，尤其在 `iterPickClient` 方法中更為明顯。
        # 預先提取仿用戶門號，等到夠用時才繼續運行程式

        # 父親帳戶 仿用戶的頭子
        self.ysUsablePapaClient = papaPhone != 0
        self._papaPhone = papaPhone

    # if phoneNumber == '+8869xxx', input '8869xxx' (str)
    async def _login(self, phoneNumber: str = '') -> TelegramClient:
        sessionPath = self.niUsersPhoneChoose.getSessionPath(phoneNumber)
        sessionPathPart = self.niUsersPhoneChoose.getSessionPath(
            phoneNumber,
            noExt = True
        )

        if not os.path.exists(sessionPath):
            raise errors.UserNotAuthorized(errors.errMsg.UserNotAuthorized)

        client = TelegramClient(
            self.niUsersPhoneChoose.getSessionPath(phoneNumber, noExt = True),
            self._apiId,
            self._apiHash
        )
        await client.connect()

        if not await client.is_user_authorized():
            raise errors.UserNotAuthorized(errors.errMsg.UserNotAuthorized)

        if phoneNumber != self._papaPhone:
            meInfo = await client.get_me()
            self._clientInfoList.append({
                'id': phoneNumber,
                'userId': meInfo.id,
                'client': client,
            })

        return client

    def lookforClientInfo(self,
            idCode: typing.Union[str, int]) -> typing.Union[TelegramClient, None]:
        clientInfoList = self._clientInfoList
        for clientInfo in clientInfoList:
            if clientInfo['id'] == idCode or clientInfo['userId'] == idCode:
                return clientInfo
        return None

    @contextlib.asynccontextmanager
    async def usePapaClient(self) -> TelegramClient:
        if not self.ysUsablePapaClient:
            raise errors.WhoIsPapa(errors.errMsg.WhoIsPapa)

        papaPhone = self._papaPhone

        while True:
            if self.niUsersPhoneChoose.lockPhone(papaPhone):
                client = await self._login(papaPhone)
                yield client
                break

            await asyncio.sleep(1)

        self.niUsersPhoneChoose.releaseLockPhone(papaPhone)

    async def pickClient(self) -> TelegramClient:
        clientInfoList = self._clientInfoList
        clientInfoListLength = len(clientInfoList)
        if clientInfoListLength < self._clientCountLimit:
            phoneNumber = await self.niUsersPhoneChoose.pickPhone()
            client = await self._login(phoneNumber)
            return client

        pickIdx = self._pickClientIdx % clientInfoListLength
        self._pickClientIdx = pickIdx + 1
        return clientInfoList[pickIdx]['client']

    async def iterPickClient(self, loopLimit: int = 1) -> TelegramClient:
        if loopLimit == 0: return

        clientCountLimit = self._clientCountLimit
        clientInfoList = self._clientInfoList
        clientInfoListLength = len(clientInfoList)
        loopTimes = 0

        # 若當前擁有的仿用戶數量不足則需補充
        if clientInfoListLength < clientCountLimit:
            for idx in range(clientInfoListLength):
                yield clientInfoList[idx]['client']
            for idx in range(clientInfoListLength, clientCountLimit):
                phoneNumber = await self.niUsersPhoneChoose.pickPhone()
                await asyncio.sleep(1)
                client = await self._login(phoneNumber)
                yield client

            if loopLimit == 1:
                return
            loopTimes = clientCountLimit

        clientInfoListLength = len(clientInfoList)
        maxLoopTimes = clientInfoListLength * loopLimit
        while True:
            idx = loopTimes % clientInfoListLength
            yield clientInfoList[idx]['client']
            if loopLimit != -1:
                loopTimes += 1
                if loopTimes >= maxLoopTimes:
                    break

    def release(self, *args):
        self.niUsersPhoneChoose.releaseLockPhone(*args)

    # TODO 好像不用 stop

