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


__all__ = ['TgBaseTool']


TelegramClient = telethon.TelegramClient


class TgTypeing():
    InputPeer = typing.Union[
        telethon.types.InputPeerEmpty,
        telethon.types.InputPeerSelf,
        telethon.types.InputPeerChat,
        telethon.types.InputPeerUser,
        telethon.types.InputPeerChannel,
        telethon.types.InputPeerUserFromMessage,
        telethon.types.InputPeerChannelFromMessage,
    ]


class _TgChanData_NiUsers():
    def __init__(self, sessionDirPath: str = '', papaPhone: str = ''):
        self._sessionDirPath = sessionDirPath
        if not os.path.exists(sessionDirPath):
            os.makedirs(sessionDirPath)

        self.chanData = utils.chanData.ChanData()
        if self.chanData.getSafe('.niUsers') == None:
            self.chanData.set('.niUsers', {
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
        niUsers = self.chanData.get('.niUsers')

        bandInfos = niUsers['bandInfos']
        bandInfosLength = len(bandInfos)
        if bandInfosLength == 0:
            return niUsers

        bands = niUsers['bandList']
        nowTimeMs = utils.novice.dateNowTimestamp()
        for idx in range(bandInfosLength):
            bandInfo = bandInfos[idx]
            if bandInfo['bannedWaitTimeMs'] < nowTimeMs:
                del bandInfos[idx]
                bands.remove(bandInfo['id'])

        return niUsers

    _regexSessionName = r'^telethon-(\d+).session$'

    def getUsablePhones(self) -> list:
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
        niUsers = self.chanData.get('.niUsers')

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
        if os.path.exists(sessionPath):
            os.remove(sessionPath)
            self._pushCemeteryData_chanData(phoneNumber)
            return self.chanData.opt('jsonarrappend', '.niUsers.cemetery', {
                'id': phoneNumber,
                'message': '{} Error: {}'.format(type(err), err),
            })
        self.chanData.store()
        return False

    def pushBandData(self, phoneNumber: str, dt: datetime.datetime) -> bool:
        bands = self.chanData.get('.niUsers.bandList')
        if utils.novice.indexOf(bands, phoneNumber) == -1:
            self.chanData.opt('jsonarrappend', '.niUsers.bandList', phoneNumber)
            return self.chanData.opt('jsonarrappend', '.niUsers.bandInfos', {
                'id': phoneNumber,
                'bannedWaitDate': utils.novice.dateStringify(dt),
                'bannedWaitTimeMs': utils.novice.dateTimestamp(dt)
            })
        return False

    @utils.chanData.ChanData.dFakeLockSet(memberPath = '.niUsers.lockList', maxTimes = 1)
    def _lockPhone_chanData(self, lockList: list) -> list:
        return lockList

    def lockPhone(self, phoneNumber: str) -> bool:
        locks = self.chanData.get('.niUsers.lockList')
        if utils.novice.indexOf(locks, phoneNumber) == -1:
            locks.append(phoneNumber)
            if self._lockPhone_chanData(locks):
                self.pickPhones.append(phoneNumber)
                return True
        return False

    @utils.chanData.ChanData.dFakeLockSet(memberPath = '.niUsers.lockList')
    def _unlockPhones_chanData(self, lockPhoneList: list) -> list:
        locks = self.chanData.get('.niUsers.lockList')
        for phoneNumber in lockPhoneList:
            phoneIdx = utils.novice.indexOf(locks, phoneNumber)
            if phoneIdx != -1:
                del locks[phoneIdx]
        return locks

    def unlockPhones(self, *args):
        pickPhones = self.pickPhones
        if len(args) == 0:
            self._unlockPhones_chanData(pickPhones)
            pickPhones.clear()
        else:
            unlockPhones = args[0]
            self._unlockPhones_chanData(unlockPhones)
            for phoneNumber in unlockPhones:
                phoneIdx = utils.novice.indexOf(pickPhones, phoneNumber)
                if phoneIdx != -1:
                    del pickPhones[phoneIdx]
        self.chanData.store()

class _TgChanData(utils.chanData.ChanData):
    def __init__(self):
        if self.getSafe('.blackGuy') == None:
            self.set('.blackGuy', {
                'infos': [],
                'list': [],
            })
            self.set('.log', [])

    @utils.chanData.ChanData.dFakeLockSet(memberPath = '.blackGuy', ysStore = True)
    def pushLog(self, txt: str) -> None:
        logNote = self.get('.log')
        logNote.append('Date: {}; Txt: {}'.format(
            utils.novice.dateStringify(utils.novice.dateNow()),
            txt
        ))

    @utils.chanData.ChanData.dFakeLockSet(memberPath = '.blackGuy', ysStore = True)
    def pushGuy(self, peer: TgTypeing.InputPeer, err: Exception) -> dict:
        blackGuy = self.get('.blackGuy')
        blackGuyInfos = blackGuy['infos']
        blackGuyList = blackGuy['list']

        userId = peer.id
        if utils.novice.indexOf(blackGuyList, userId) == -1:
            blackGuyList.append(userId)
            username = peer.username
            if username != '':
                blackGuyList.append(username)
            blackGuyInfos.append({
                'userId': peer.id,
                'username': username,
                'message': '{} Error: {}'.format(type(err), err),
            })

        return blackGuy


class _TgNiUsers():
    def __init__(self, *args):
        self._initTgNiUsers(*args)

    def _initTgNiUsers(self,
            apiId: str,
            apiHash: str,
            sessionDirPath: str,
            clientCountLimit: int = 3,
            papaPhone: str = '') -> None:
        self._apiId = apiId
        self._apiHash = apiHash
        self._pickClientIdx = -1
        self._clientInfoList = []

        self._clientCountLimit = clientCountLimit if clientCountLimit > 0 else 3
        self.chanDataNiUsers = _TgChanData_NiUsers(sessionDirPath, papaPhone)

        # 父親帳戶 仿用戶的頭子
        self.ysUsablePapaClient = papaPhone != ''
        self._papaPhone = papaPhone

        # 異常退出時執行
        @utils.novice.dOnExit
        def onExit():
            self.release()

    async def init(self) -> None:
        clientCount = self._clientCountLimit
        chanDataNiUsers = self.chanDataNiUsers

        # 30 * 6 sec ~= 3 min
        for idxLoop in range(60):
            if idxLoop >= 30:
                raise errors.PickPhoneMoreTimes(errors.errMsg.PickPhoneMoreTimes)

            if idxLoop % 3 == 0:
                usablePhones = chanDataNiUsers.getUsablePhones()

            niUsers = chanDataNiUsers.chanData.get('.niUsers')
            bands = niUsers['bandList']
            locks = niUsers['lockList']

            if len(usablePhones) - len(bands) - len(locks) < clientCount:
                await asyncio.sleep(6)
                continue

            pickClients = await self._init_loginAll(usablePhones, bands, locks, clientCount)
            if pickClients == None:
                await asyncio.sleep(1)
                continue

            await self._init_register(pickClients)
            break

    async def _init_loginAll(self,
            usablePhones: list,
            bandPhones: list,
            lockPhones: list,
            clientCount: int) -> typing.Union[None, typing.List[TelegramClient]]:
        chanDataNiUsers = self.chanDataNiUsers

        pickPhones = []
        pickClients = []

        usablePhonesLength = len(usablePhones)
        # 避免頻繁使用同一帳號
        indexStart = random.randrange(0, usablePhonesLength)
        for idx in range(indexStart, usablePhonesLength + indexStart):
            phoneNumber = usablePhones[idx % usablePhonesLength]

            if utils.novice.indexOf(bandPhones, phoneNumber) != -1 \
                    or utils.novice.indexOf(lockPhones, phoneNumber) != -1:
                continue

            if chanDataNiUsers.lockPhone(phoneNumber):
                client = await self._login(phoneNumber)
                if client != None:
                    pickPhones.append(phoneNumber)
                    pickClients.append(client)
                    if len(pickClients) == clientCount:
                        return pickClients

        chanDataNiUsers.unlockPhones(pickPhones)
        for client in pickClients:
            await client.disconnect()
        return None

    async def _init_register(self, clientList: list) -> None:
        for client in clientList:
            meInfo = await client.get_me()
            self._clientInfoList.append({
                'id': meInfo.phone,
                'userId': meInfo.id,
                'client': client,
            })

    # if phoneNumber == '+8869xxx', input '8869xxx' (str)
    async def _login(self, phoneNumber: str) -> typing.Union[None, TelegramClient]:
        chanDataNiUsers = self.chanDataNiUsers
        sessionPath = chanDataNiUsers.getSessionPath(phoneNumber)

        if not os.path.exists(sessionPath):
            raise errors.UserNotAuthorized(errors.errMsg.UserNotAuthorized)

        client = TelegramClient(
            chanDataNiUsers.getSessionPath(phoneNumber, noExt = True),
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
            err = errors.UserNotAuthorized(errors.errMsg.UserNotAuthorized)
            chanDataNiUsers.pushCemeteryData(phoneNumber, err)
            return None

        return client

    def release(self, *args):
        self._clientInfoList.clear()
        self.chanDataNiUsers.unlockPhones(*args)

    async def reinit(self):
        self.release()
        await self.init()

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
            if self.chanDataNiUsers.lockPhone(papaPhone):
                client = await self._login(papaPhone)
                yield client
                await client.disconnect()
                break

            await asyncio.sleep(1)

        self.chanDataNiUsers.unlockPhones([papaPhone])

    async def pickClient(self) -> TelegramClient:
        clientInfoList = self._clientInfoList
        self._pickClientIdx += 1
        pickIdx = self._pickClientIdx % len(clientInfoList)
        return clientInfoList[pickIdx]['client']

    async def iterPickClient(self,
            circleLimit: int = 1,
            circleInterval: float = 1) -> TelegramClient:
        if not (circleLimit == -1 or 0 < circleLimit):
            return

        clientInfoList = self._clientInfoList
        clientInfoListLength = len(clientInfoList)
        maxLoopTimes = clientInfoListLength * circleLimit if circleLimit != -1 else -1

        prevTimeMs = utils.novice.dateNowTimestamp()
        idxLoop = 0
        while True:
            pickIdx = idxLoop % clientInfoListLength

            if circleInterval > 0 and idxLoop != 0 and pickIdx == 0:
                nowTimeMs = utils.novice.dateNowTimestamp()
                intervalTimeMs = circleInterval - ((nowTimeMs - prevTimeMs) / 1000)
                if intervalTimeMs > 0:
                    print('wait {} second'.format(intervalTimeMs))
                    await asyncio.sleep(intervalTimeMs)
                    prevTimeMs = utils.novice.dateNowTimestamp()
                else:
                    prevTimeMs = nowTimeMs

            client = clientInfoList[pickIdx]['client']
            yield client

            idxLoop += 1
            if 0 < maxLoopTimes and maxLoopTimes <= idxLoop:
                break


class TgBaseTool(_TgNiUsers):
    def __init__(self,
            apiId: str,
            apiHash: str,
            sessionDirPath: str,
            clientCountLimit: int = 3,
            papaPhone: str = 0):
        self._initTgNiUsers(
            apiId = apiId,
            apiHash = apiHash,
            sessionDirPath = sessionDirPath,
            clientCountLimit = clientCountLimit,
            papaPhone = papaPhone
        )
        self.chanData = _TgChanData()

    def getRandId(self):
        return random.randrange(1000000, 9999999)

    def joinGroup(self, client: TelegramClient, groupCode: str) -> telethon.types.Updates:
        # TODO 檢查是否已經入群
        # 透過 `functions.messages.GetDialogsRequest` 請求來達成 ?
        # 但即便已經入群 `functions.channels.JoinChannelRequest` 請求也能成功執行
        return client(telethon.functions.channels.JoinChannelRequest(
            channel = groupCode
        ))

    def leaveGroup(self, client: TelegramClient, groupCode: str) -> telethon.types.Updates:
        return client(telethon.functions.channels.LeaveChannelRequest(
            channel = groupCode
        ))

