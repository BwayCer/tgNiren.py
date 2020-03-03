#!/usr/bin/env python3


import typing
import os
import datetime
import random
import asyncio
import contextlib
import telethon.sync as telethon
import utils.chanData
import utils.novice as novice
import tgkream.errors as errors
from tgkream.utils import TgTypeing, TgSession


__all__ = ['errors', 'telethon', 'TgTypeing', 'TgBaseTool', 'tgTodoFunc']


TelegramClient = telethon.TelegramClient


class _TgChanData_NiUsers(TgSession):
    def __init__(self, sessionDirPath: str = '', papaPhone: str = ''):
        TgSession.__init__(self, sessionDirPath)

        self.chanData = utils.chanData.ChanData()
        if self.chanData.getSafe('.niUsers') == None:
            self.chanData.data['niUsers'] = {
                'cemetery': [],
                'bandInfos': [],
                'bandList': [],
                'lockList': [],
            }
        else:
            self.updateBandInfo()

        self._papaPhone = papaPhone
        self.pickPhones = []

    def updateBandInfo(self) -> None:
        niUsers = self.chanData.data['niUsers']

        bandInfos = niUsers['bandInfos']
        bandInfosLength = len(bandInfos)
        if bandInfosLength == 0:
            return

        bands = niUsers['bandList']
        nowTimeMs = novice.dateNowTimestamp()
        for idx in range(bandInfosLength - 1, -1, -1):
            bandInfo = bandInfos[idx]
            if bandInfo['bannedWaitTimeMs'] < nowTimeMs:
                del bandInfos[idx]
                bands.remove(bandInfo['id'])

        self.chanData.store()

    def getUsablePhones(self) -> list:
        phones = self.getOwnPhones()
        papaPhoneIdx = novice.indexOf(phones, self._papaPhone)
        if papaPhoneIdx != -1:
            del phones[papaPhoneIdx]
        return phones

    def pushCemeteryData(self, phoneNumber: str, err: Exception) -> None:
        sessionPath = self.getSessionPath(phoneNumber)
        if os.path.exists(sessionPath):
            os.remove(sessionPath)

        self._pushCemeteryData_chanData(phoneNumber)
        niUsers = self.chanData.data['niUsers']

        locks = niUsers['lockList']
        locksIdx = novice.indexOf(locks, phoneNumber)
        if locksIdx != -1:
            del locks[locksIdx]

        bands = niUsers['bandList']
        bandsIdx = novice.indexOf(bands, phoneNumber)
        if bandsIdx != -1:
            del bands[bandsIdx]
            bandInfos = niUsers['bandInfos']
            bandInfosLength = len(bandInfos)
            for bandInfosIdx in range(bandInfosLength):
                bandInfo = bandInfos[bandInfosIdx]
                if bandInfo['id'] == phoneNumber:
                    del bandInfos[bandInfosIdx]
                    break

        niUsers['cemetery'].append({
            'id': phoneNumber,
            'message': '{} Error: {}'.format(type(err), err),
        })

        self.chanData.store()

    def pushBandData(self, phoneNumber: str, dt: datetime.datetime) -> bool:
        niUsers = self.chanData.data['niUsers']
        bands = niUsers['bandList']
        if novice.indexOf(bands, phoneNumber) == -1:
            bands.append(phoneNumber)
            niUsers['bandInfos'].append({
                'id': phoneNumber,
                'bannedWaitDate': novice.dateStringify(dt),
                'bannedWaitTimeMs': novice.dateTimestamp(dt)
            })
        return False

    def lockPhone(self, phoneNumber: str) -> bool:
        locks = self.chanData.data['niUsers']['lockList']
        if novice.indexOf(locks, phoneNumber) == -1:
            locks.append(phoneNumber)
            self.pickPhones.append(phoneNumber)
            return True
        return False

    def _unlockPhones_chanData(self, lockPhoneList: list) -> None:
        locks = self.chanData.data['niUsers']['lockList']
        for phoneNumber in lockPhoneList:
            phoneIdx = novice.indexOf(locks, phoneNumber)
            if phoneIdx != -1:
                del locks[phoneIdx]

    def unlockPhones(self, *args):
        pickPhones = self.pickPhones
        if len(args) == 0:
            self._unlockPhones_chanData(pickPhones)
            pickPhones.clear()
        else:
            unlockPhones = args[0]
            self._unlockPhones_chanData(unlockPhones)
            for phoneNumber in unlockPhones:
                phoneIdx = novice.indexOf(pickPhones, phoneNumber)
                if phoneIdx != -1:
                    del pickPhones[phoneIdx]
        self.chanData.store()

class _TgChanData(utils.chanData.ChanData):
    def __init__(self):
        utils.chanData.ChanData.__init__(self)
        if self.getSafe('.blackGuy') == None:
            self.data['blackGuy'] = {
                'infos': [],
                'list': [],
            }

    def pushGuy(self, peer: TgTypeing.Peer, err: Exception) -> None:
        blackGuy = self.data['blackGuy']
        blackGuyInfos = blackGuy['infos']
        blackGuyList = blackGuy['list']

        userId = peer.id
        if novice.indexOf(blackGuyList, userId) == -1:
            blackGuyList.append(userId)
            username = peer.username
            if username != '':
                blackGuyList.append(username)
            blackGuyInfos.append({
                'userId': peer.id,
                'username': username,
                'message': '{} Error: {}'.format(type(err), err),
            })

            self.chanData.store()


class _TgNiUsers():
    def __init__(self,
            apiId: str,
            apiHash: str,
            sessionDirPath: str,
            clientCount: int = 3,
            papaPhone: str = '') -> None:
        self._apiId = apiId
        self._apiHash = apiHash
        self._pickClientIdx = -1
        self._clientInfoList = []

        self.clientCount = clientCount if clientCount > 0 else 3
        self.chanDataNiUsers = _TgChanData_NiUsers(sessionDirPath, papaPhone)

        # 父親帳戶 仿用戶的頭子
        self.ysUsablePapaClient = papaPhone != ''
        self._papaPhone = papaPhone

        self._currentClient = None

        # 異常退出時執行
        @novice.dOnExit
        def onExit():
            # NOTE 2020.03.02
            # 無須在退出時刻意執行 `asyncio.run(self.release())` 協助 Telethon 斷開連線，
            # 否則會拋出以下警告
            #     /home/.../.venv/lib/python3.8/site-packages/telethon/client/telegrambaseclient.py:498:
            #       RuntimeWarning: coroutine 'TelegramBaseClient._disconnect_coro' was never awaited
            #         pass
            #     RuntimeWarning: Enable tracemalloc to get the object allocation traceback
            self.chanDataNiUsers.unlockPhones()

    async def init(self) -> None:
        clientCount = self.clientCount
        chanDataNiUsers = self.chanDataNiUsers

        # 3 * 3 sec ~= 9 sec
        idxLoop = -1
        while True:
            idxLoop += 1
            print('init-{}'.format(idxLoop))
            if idxLoop >= 3:
                raise errors.PickPhoneMoreTimes(errors.errMsg.PickPhoneMoreTimes)

            if idxLoop % 3 == 0:
                usablePhones = chanDataNiUsers.getUsablePhones()

            niUsers = chanDataNiUsers.chanData.data['niUsers']
            bands = niUsers['bandList']
            locks = niUsers['lockList']

            if len(usablePhones) - len(bands) - len(locks) < clientCount:
                await asyncio.sleep(3)
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

            if novice.indexOf(bandPhones, phoneNumber) != -1 \
                    or novice.indexOf(lockPhones, phoneNumber) != -1:
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
            myInfo = await client.get_me()
            self._clientInfoList.append({
                'id': myInfo.phone,
                'userId': myInfo.id,
                'client': client,
            })

    # if phoneNumber == '+8869xxx', input '8869xxx' (str)
    async def _login(self, phoneNumber: str) -> typing.Union[None, TelegramClient]:
        chanDataNiUsers = self.chanDataNiUsers
        sessionPath = chanDataNiUsers.getSessionPath(phoneNumber)

        if not os.path.exists(sessionPath):
            raise errors.UserNotAuthorized(
                errors.errMsg.SessionFileNotExistsTemplate.format(phoneNumber)
            )

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
            err = errors.UserNotAuthorized(
                errors.errMsg.UserNotAuthorizedTemplate.format(phoneNumber)
            )
            chanDataNiUsers.pushCemeteryData(phoneNumber, err)
            return None

        return client

    async def release(self, *args):
        clientInfoList = self._clientInfoList
        for clientInfo in clientInfoList:
            # 若是無 client，`client.disconnect()` 的回傳值是 None ?!
            result = clientInfo['client'].disconnect()
            if asyncio.iscoroutine(result):
                result = await result
        clientInfoList.clear()
        self.chanDataNiUsers.unlockPhones(*args)

    async def reinit(self):
        await self.release()
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
        error = None

        while True:
            if self.chanDataNiUsers.lockPhone(papaPhone):
                client = await self._login(papaPhone)

                try:
                    yield client
                except Exception as err:
                    error = err

                await client.disconnect()
                break

            await asyncio.sleep(1)

        self.chanDataNiUsers.unlockPhones([papaPhone])

        if error != None:
            raise error

    async def pickCurrentClient(self, client: TelegramClient = None) -> TelegramClient:
        if client != None:
            self._currentClient = client
        elif self._currentClient == None:
            await self.pickClient()

        return self._currentClient

    async def pickClient(self) -> TelegramClient:
        clientInfoList = self._clientInfoList
        self._pickClientIdx += 1
        pickIdx = self._pickClientIdx % len(clientInfoList)
        self._currentClient = clientInfoList[pickIdx]['client']
        return self._currentClient

    # TODO
    # 當調用的迴圈用 break 跳出時，無法使用 try finally 捕獲，
    # 因而無法自動回復 `self._currentClient` 的原始值
    async def iterPickClient(self,
            circleLimit: int = 1,
            circleInterval: float = 1,
            whichNiUsers: bool = False) -> TelegramClient:
        if not (circleLimit == -1 or 0 < circleLimit):
            return

        clientInfoList = self._clientInfoList
        clientInfoListLength = len(clientInfoList)
        maxLoopTimes = clientInfoListLength * circleLimit if circleLimit != -1 else -1

        prevTimeMs = novice.dateNowTimestamp()
        idxLoop = 0
        while True:
            pickIdx = idxLoop % clientInfoListLength

            if circleInterval > 0 and idxLoop != 0 and pickIdx == 0:
                nowTimeMs = novice.dateNowTimestamp()
                intervalTimeMs = circleInterval - ((nowTimeMs - prevTimeMs) / 1000)
                if intervalTimeMs > 0:
                    print('wait {} second'.format(intervalTimeMs))
                    await asyncio.sleep(intervalTimeMs)
                    prevTimeMs = novice.dateNowTimestamp()
                else:
                    prevTimeMs = nowTimeMs

            clientInfo = clientInfoList[pickIdx]
            self._currentClient = clientInfoList[pickIdx]['client']
            if whichNiUsers:
                yield {
                    'id':clientInfo['id'],
                    'userId': clientInfo['userId'],
                    'client': self._currentClient,
                }
            else:
                yield self._currentClient

            idxLoop += 1
            if 0 < maxLoopTimes and maxLoopTimes <= idxLoop:
                break

class TgBaseTool(_TgNiUsers):
    def __init__(self,
            apiId: str,
            apiHash: str,
            sessionDirPath: str,
            clientCount: int = 3,
            papaPhone: str = 0):
        _TgNiUsers.__init__(
            self,
            apiId = apiId,
            apiHash = apiHash,
            sessionDirPath = sessionDirPath,
            clientCount = clientCount,
            papaPhone = papaPhone
        )
        self.chanData = _TgChanData()

    def getRandId(self):
        return random.randrange(1000000, 9999999)

    # TgTypeing.Peer
    async def getPeerTypeName(self, peer: TgTypeing.AutoInputPeer) -> str:
        if type(peer) == str:
            client = await self.pickCurrentClient()
            inputPeer = await client.get_entity(peer)
        else:
            inputPeer = peer

        inputPeerType = type(inputPeer)
        if inputPeerType == telethon.types.Chat:
            inputPeerTypeName = 'Chat'
        elif inputPeerType == telethon.types.User:
            inputPeerTypeName = 'User'
        elif inputPeerType == telethon.types.Channel:
            inputPeerTypeName = 'Channel'

        return inputPeerTypeName

    def joinGroup(self,
            client: TelegramClient,
            groupPeer: TgTypeing.AutoInputPeer) -> telethon.types.Updates:
        # TODO 檢查是否已經入群
        # 透過 `functions.messages.GetDialogsRequest` 請求來達成 ?
        # 但即便已經入群 `functions.channels.JoinChannelRequest` 請求也能成功執行
        return client(telethon.functions.channels.JoinChannelRequest(
            channel = groupPeer
        ))

    def leaveGroup(self,
            client: TelegramClient,
            groupPeer: TgTypeing.AutoInputPeer) -> telethon.types.Updates:
        return client(telethon.functions.channels.LeaveChannelRequest(
            channel = groupPeer
        ))

    async def getParticipants(self,
            client: TelegramClient,
            groupPeer: str,
            offset: int = 0,
            ynRealUser: bool = True,
            excludedUserList: list = [],
            amount: int = 200000) -> typing.Tuple[int, list]:
        # 每次請求用戶數
        pageAmount = amount * 2 + 10 # 估值 猜想排除的用戶數
        pageAmount = pageAmount if pageAmount < 100 else 100
        ynHasExcludedUsers = len(excludedUserList) != 0,
        pickIdx = pickRealIdx = offset
        channelParticipantsSearch = telethon.types.ChannelParticipantsSearch(q = '')

        ynBreak = False
        users = []
        while len(users) < amount:
            participants = await client(
                telethon.functions.channels.GetParticipantsRequest(
                    channel = groupPeer,
                    filter = channelParticipantsSearch,
                    offset = pickIdx,
                    limit = pageAmount,
                    hash = 0
                )
            )

            if not participants.participants:
                break  # No more participants left

            for user in participants.users:
                pickRealIdx += 1

                # 排除 自己, 已刪除帳號, 機器人
                # type(user.is_self) == type(user.deleted) == type(user.bot) == bool
                if ynRealUser and (user.is_self or user.deleted or user.bot):
                    continue
                # 排除欲除外用戶
                if ynHasExcludedUsers \
                        and novice.indexOf(excludedUserList, user.id) != -1:
                    continue
                # 排除仿用戶
                if self.lookforClientInfo(user.id) != None:
                    continue

                # 可用物件有:
                #   id, username, first_name, last_name
                #   access_hash
                users.append(user)

                if len(users) == amount:
                    ynBreak = True
                    break

            if ynBreak:
                break

            pickIdx += pageAmount

        return (pickRealIdx, users)


# TODO 因時程關係未拆分程式碼

class tgTodoFunc():
    def getNiUsersStatusInfo():
        chanDataNiUsers = _TgChanData_NiUsers(
            novice.py_dirname + '/' + novice.py_env['tgSessionDirPath'],
            novice.py_env['papaPhoneNumber']
        )
        usablePhones = chanDataNiUsers.getUsablePhones()
        niUsers = chanDataNiUsers.chanData.data['niUsers']
        bands = niUsers['bandList']
        locks = niUsers['lockList']
        return {'allCount': len(usablePhones), 'lockCount':  len(bands) + len(locks)}

