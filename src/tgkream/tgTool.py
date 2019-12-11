#!/usr/bin/env python3


from typing import Union
import os
import datetime
import random
import re
import asyncio
from telethon.sync import TelegramClient
import utils.chanData
import utils.novice


__all__ = ['TgLoginTool']


class _NiUsersPhoneChoose():
    def __init__(self, sessionDirPath: str = ''):
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
                bandsIdx = utils.novice.indexOf(bands, bandInfo['id'])
                del bandInfos[idx]
                del bands[bandsIdx]

        return niUsers

    _regexSessionName = r'^telethon-(\d+).session$'

    def _getUsablePhones(self) -> list:
        phones = []
        files = os.listdir(self._sessionDirPath)
        for fileName in files:
            if os.path.isfile(os.path.join(self._sessionDirPath, fileName)):
                matchTgCode = re.search(self._regexSessionName, fileName)
                if matchTgCode:
                    phones.append(matchTgCode.group(1))
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
        times = -1
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


class TgLoginTool():
    def __init__(self, apiId: str, apiHash: str, sessionPrefix: str = ''):
        self._sessionPrefix = sessionPrefix
        self._apiId = apiId
        self._apiHash = apiHash
        self._pickClientIdx = 0
        self._clientInfoList = []

    # if phoneNumber == '+8869xxx', input 8869xxx (int)
    def login(self, phoneNumber: int) -> None:
        sessionFilePathPart = self._sessionPrefix + str(phoneNumber)

        sessionDirPath = os.path.dirname(sessionFilePathPart)
        if not os.path.exists(sessionDirPath):
            os.makedirs(sessionDirPath)

        client = TelegramClient(
            sessionFilePathPart,
            self._apiId,
            self._apiHash
        )
        client.connect()
        if not client.is_user_authorized():
            client.send_code_request(phoneNumber)
            verifiedCode = input('login {}, Enter the code: '.format(phoneNumber))
            client.sign_in(phoneNumber, verifiedCode)

        meInfo = client.get_me()
        self._clientInfoList.append({
            'id': phoneNumber,
            'userId': meInfo.id,
            'client': client,
        })

    def _lookforClientInfo(self, idCode: int) -> Union[TelegramClient, None]:
        clientInfoList = self._clientInfoList
        for clientInfo in clientInfoList:
            if clientInfo['id'] == idCode or clientInfo['userId'] == idCode:
                return clientInfo
        return None

    def lookforClient(self, idCode: int) -> Union[TelegramClient, None]:
        clientInfo = self._lookforClientInfo(idCode)
        if clientInfo != None:
            return clientInfo['client']
        return None

    def theClient(self, idCode: int = 0) -> TelegramClient:
        if idCode == 0:
            clientInfoList = self._clientInfoList
            if len(clientInfoList) > 0:
                return clientInfoList[0]['client']

        clientInfo = self._lookforClientInfo(idCode)
        if clientInfo != None:
            return clientInfo['client']

        raise KeyError('The {} id not found'.format(idCode))

    def pickClient(self) -> TelegramClient:
        clientInfoList = self._clientInfoList
        clientListLength = len(clientInfoList)
        pickIdx = self._pickClientIdx + 1

        if clientListLength == 0:
            raise Exception('No telegram connection established')

        idx = self._pickClientIdx = pickIdx % clientListLength
        return clientInfoList[idx]['client']

    def removeClient(self, idCode: int) -> bool:
        clientInfo = self._lookforClientInfo(idCode)
        if clientInfo == None:
            return False

        self._clientInfoList.remove(clientInfo)
        return True

    def removePickClient(self) -> True:
        clientInfoList = self._clientInfoList
        clientInfoList.remove(clientInfoList[self._pickClientIdx])
        return True

    # TODO 好像不用 stop

