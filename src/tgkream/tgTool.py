#!/usr/bin/env python3


import typing
import os
import datetime
import random
import asyncio
import contextlib
import telethon as telethon
import utils.chanData
import utils.novice as novice
import tgkream.errors as errors
from tgkream.utils import TgTypeing, TgSession, TgDefaultInit


__all__ = [
    'errors', 'knownError',
    'telethon', 'TgTypeing', 'TgDefaultInit', 'TgBaseTool'
]


TelegramClient = telethon.TelegramClient

knownError = errors.knownError


class _TgChanData_NiUsers(TgSession):
    def __init__(self, sessionPrifix: str = '', papaPhone: str = ''):
        TgSession.__init__(self, sessionPrifix)

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
        nowTimeMs = novice.dateUtcNowTimestamp()
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
            self.mvSessionPath(phoneNumber, toAddPrifix = 'cemetery')

        niUsers = self.chanData.data['niUsers']

        locks = niUsers['lockList']
        lockIdx = novice.indexOf(locks, phoneNumber)
        if lockIdx != -1:
            del locks[lockIdx]

        bands = niUsers['bandList']
        bandIdx = novice.indexOf(bands, phoneNumber)
        if bandIdx != -1:
            del bands[bandIdx]
            bandInfos = niUsers['bandInfos']
            bandInfosLength = len(bandInfos)
            for bandInfoIdx in range(bandInfosLength):
                bandInfo = bandInfos[bandInfoIdx]
                if bandInfo['id'] == phoneNumber:
                    del bandInfos[bandInfoIdx]
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
                'bannedWaitDate': novice.dateUtcStringify(dt),
                'bannedWaitTimeMs': novice.dateUtcTimestamp(dt)
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

    def unlockPhones(self, *args) -> None:
        pickPhones = self.pickPhones
        if len(args) == 0:
            self._unlockPhones_chanData(pickPhones)
            pickPhones.clear()
        else:
            for phoneNumber in args:
                phoneIdx = novice.indexOf(pickPhones, phoneNumber)
                if phoneIdx != -1:
                    self._unlockPhones_chanData([phoneNumber])
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
            apiId: int,
            apiHash: str,
            sessionPrifix: str,
            clientCount: int = 3,
            papaPhone: str = '') -> None:
        self._apiId = apiId
        self._apiHash = apiHash
        self._pickClientIdx = -1
        self._clientInfoList = []

        self.clientCount = clientCount if clientCount > 0 else 3
        self.chanDataNiUsers = _TgChanData_NiUsers(sessionPrifix, papaPhone)

        # 父親帳戶 仿用戶的頭子
        self.ysUsablePapaClient = papaPhone != ''
        self._papaPhone = papaPhone

        self._currentClientInfo = None

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
        clientCount = self.clientCount - len(self._clientInfoList)
        if not clientCount > 0:
            return

        task = asyncio.current_task()
        taskName = task.get_name()
        print('-> {}: {}'.format(task.get_name(), task.get_coro()))

        chanDataNiUsers = self.chanDataNiUsers
        usablePhones = chanDataNiUsers.getUsablePhones()
        usablePhonesLength = len(usablePhones)
        niUsers = chanDataNiUsers.chanData.data['niUsers']
        bandPhones = niUsers['bandList']
        lockPhones = niUsers['lockList']

        # 3 * 3 sec ~= 9 sec
        idxLoop = 0
        while True:
            idxLoop += 1
            print('init-{}'.format(idxLoop))

            if idxLoop > 3:
                raise errors.PickPhoneMoreTimes(errors.errMsg.PickPhoneMoreTimes)

            if usablePhonesLength - len(bandPhones) - len(lockPhones) < clientCount:
                await asyncio.sleep(3)
                usablePhones = chanDataNiUsers.getUsablePhones()
                usablePhonesLength = len(usablePhones)
                continue

            isSuccessPick = False
            tobePickedLength = clientCount
            pickPhones = []
            pickClients = []

            # 避免頻繁使用同一帳號
            indexStart = random.randrange(0, usablePhonesLength)
            for idx in range(indexStart, usablePhonesLength + indexStart):
                phoneNumber = usablePhones[idx % usablePhonesLength]

                if usablePhonesLength - len(bandPhones) - len(lockPhones) \
                        < tobePickedLength:
                    break

                if novice.indexOf(bandPhones, phoneNumber) != -1 \
                        or novice.indexOf(lockPhones, phoneNumber) != -1:
                    continue

                if chanDataNiUsers.lockPhone(phoneNumber):
                    client = await self._login(phoneNumber)
                    if client == None:
                        chanDataNiUsers.unlockPhones(phoneNumber)
                    else:
                        tobePickedLength -= 1
                        pickPhones.append(phoneNumber)
                        pickClients.append(client)
                        if tobePickedLength == 0:
                            isSuccessPick = True
                            break

            if isSuccessPick:
                await self._init_register(pickClients)
                break

            for idx in range(0, len(pickClients)):
                await pickClients[idx].disconnect()
                chanDataNiUsers.unlockPhones(pickPhones[idx])

            await asyncio.sleep(1)

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
            print('_login +' + phoneNumber)
            await client.connect()
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

    async def login(self, phoneNumber: str) -> typing.Union[None, TelegramClient]:
        chanDataNiUsers = self.chanDataNiUsers

        if chanDataNiUsers.lockPhone(phoneNumber):
            client = await self._login(phoneNumber)
            if client == None:
                chanDataNiUsers.unlockPhones(phoneNumber)
            else:
                await self._init_register([client])

        return client

    async def release(self, *args):
        clientInfoList = self._clientInfoList
        if len(args) == 0:
            for clientInfo in clientInfoList:
                # 若是無 client，`client.disconnect()` 的回傳值是 None ?!
                result = clientInfo['client'].disconnect()
                if asyncio.iscoroutine(result):
                    await result
            clientInfoList.clear()
            self.chanDataNiUsers.unlockPhones()
        else:
            for phoneNumber in args:
                for clientInfoIdx in range(len(clientInfoList) - 1, -1, -1):
                    clientInfo = clientInfoList[clientInfoIdx]
                    if clientInfo['id'] == phoneNumber:
                        del clientInfoList[clientInfoIdx]
                        result = clientInfo['client'].disconnect()
                        if asyncio.iscoroutine(result):
                            await result
                        self.chanDataNiUsers.unlockPhones(phoneNumber)

    async def reinit(self):
        await self.release()
        await self.init()

    def lookforClientInfo(self,
            idCode: typing.Union[str, int]) -> typing.Union[None, dict]:
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

        self.chanDataNiUsers.unlockPhones(papaPhone)

        if error != None:
            raise error

    def pickCurrentClient(self) -> dict:
        return self._currentClientInfo \
            if self._currentClientInfo != None else self.pickClient()

    def pickClient(self) -> dict:
        clientInfoList = self._clientInfoList
        self._pickClientIdx += 1
        pickIdx = self._pickClientIdx % len(clientInfoList)
        self._currentClientInfo = clientInfoList[pickIdx].copy()
        return self._currentClientInfo

    # TODO
    # 當調用的迴圈用 break 跳出時，無法使用 try finally 捕獲，
    # 因而無法自動回復 `self._currentClientInfo` 的原始值
    async def iterPickClient(self,
            circleLimit: int = 1,
            circleInterval: float = 1) -> dict:
        if not (circleLimit == -1 or 0 < circleLimit):
            return

        clientInfoList = self._clientInfoList
        clientInfoListLength = len(clientInfoList)
        maxLoopTimes = clientInfoListLength * circleLimit if circleLimit != -1 else -1

        prevTimeMs = novice.dateUtcNowTimestamp()
        idxLoop = 0
        while True:
            pickIdx = idxLoop % clientInfoListLength

            if circleInterval > 0 and idxLoop != 0 and pickIdx == 0:
                nowTimeMs = novice.dateUtcNowTimestamp()
                intervalTimeMs = circleInterval - ((nowTimeMs - prevTimeMs) / 1000)
                if intervalTimeMs > 0:
                    print('wait {} second'.format(intervalTimeMs))
                    await asyncio.sleep(intervalTimeMs)
                    prevTimeMs = novice.dateUtcNowTimestamp()
                else:
                    prevTimeMs = nowTimeMs

            clientInfo = self._currentClientInfo = clientInfoList[pickIdx].copy()
            yield clientInfo

            idxLoop += 1
            if 0 < maxLoopTimes and maxLoopTimes <= idxLoop:
                break

class TgBaseTool(_TgNiUsers):
    def __init__(self,
            apiId: int,
            apiHash: str,
            sessionPrifix: str,
            clientCount: int = 3,
            papaPhone: str = 0):
        _TgNiUsers.__init__(
            self,
            apiId = apiId,
            apiHash = apiHash,
            sessionPrifix = sessionPrifix,
            clientCount = clientCount,
            papaPhone = papaPhone
        )
        self.chanData = _TgChanData()

    def getRandId(self):
        return random.randrange(1000000, 9999999)

    # NOTE:
    # 1. 不存在的聊天室會報錯
    # 2. 私有聊天室若未參加會報錯
    async def parsePeer(self,
            peer:  typing.Union[
                str,
                telethon.types.Chat,
                telethon.types.User,
                telethon.types.Channel,
            ]) -> dict:
        # NOTE:
        # 1. 一開始建立的群組為 `telethon.types.Chat` 類型，
        #    當更改為公開群組之後則為 `telethon.types.Channel` 類型，並固定下來。
        #    (補充: 可能使用 `get_input_entity()` 會判斷錯誤，建議使用 `get_entity()`)

        if type(peer) == str:
            client = self.pickCurrentClient()['client']
            entity = await client.get_entity(peer)
        else:
            entity = peer

        # NOTE:
        # 已知的 type(entity) 為
        #   telethon.types.Chat
        #   telethon.types.User
        #   telethon.types.Channel
        entityTypeName = entity.__class__.__name__
        isUserSet = entityTypeName == 'User'
        isBot = isUserSet and entity.bot

        if isUserSet:
            name = entity.first_name if entity.first_name != None else '---'
            if entity.last_name != None:
                name += ' ' + entity.last_name
        else:
            name = entity.title

        if entityTypeName == 'Chat':
            isGroups = True
            username = None
        else:
            isGroups = not isUserSet and entity.megagroup
            username = entity.username

        chatTypeName = 'Bot' if isBot else \
            'Group' if isGroups else \
            'User' if isUserSet else \
            'Channel'

        return {
            'id': entity.id,
            'accessHash': entity.access_hash \
                if hasattr(entity, 'access_hash') else None,
            'name': name,
            'username': username,
            'isHideUsername': username == None,
            'entityTypeName': entityTypeName,
            'chatTypeName': chatTypeName,
            'isUserSet': isUserSet,
            'isChannelSet': not isUserSet,
            'isUser': isUserSet and not isBot,
            'isBot': isBot,
            'isChannel': not isUserSet and not isGroups,
            'isGroup': isGroups,
        }

    def joinGroup(self,
            client: TelegramClient,
            groupPeer: TgTypeing.AutoInputPeer) -> telethon.types.Updates:
        # TODO 檢查是否已經入群
        # 透過 `functions.messages.GetDialogsRequest` 請求來達成 ?
        # 但即便已經入群 `functions.channels.JoinChannelRequest` 請求也能成功執行
        realUserName, isPrivate = telethon.utils.parse_username(groupPeer)
        if isPrivate:
            return client(
                telethon.functions.messages.ImportChatInviteRequest(realUserName)
            )
        else:
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
            excludedUserList: typing.Tuple[None, list] = None,
            amount: int = 200000) -> typing.Tuple[int, list]:
        # 每次請求用戶數
        pageAmount = amount * 2 + 10 # 估值 猜想排除的用戶數
        pageAmount = pageAmount if pageAmount < 100 else 100
        isHasExcludedUsers = excludedUserList != None and len(excludedUserList) != 0
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
                if isHasExcludedUsers \
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

    async def getSpeakers(self,
            client: TelegramClient,
            groupPeer: str,
            offsetDays: float,
            ynRealUser: bool = True,
            excludedUserList: typing.Tuple[None, list] = None,
            amount: typing.Tuple[None, int] = None) -> typing.List[telethon.types.User]:
        # `offsetDays`, `amount` 有效值須大於 0
        if offsetDays <= 0 or (amount != None and amount <= 0):
            return []

        isHasExcludedUsers = excludedUserList != None and len(excludedUserList) != 0
        isHasAmount = amount != None
        theDt = novice.dateUtcNowOffset(days = -1 * offsetDays)

        # NOTE: 關於 `GetHistoryRequest()` 方法
        # https://core.telegram.org/method/messages.getHistory
        # https://tl.telethon.dev/methods/messages/get_history.html
        # 1. 當對象為用戶時，沒有訊息?! (2020.11.23 紀錄)
        # 關於參數值：
        #   1. `offset_id`, `add_offset` 用於選取在特定訊息前或後的訊息，不使用則傳入 `0`。
        #   2. `offset_date`, `max_id`, `min_id` 用於選取在特定範圍內的訊息
        #      注意！ 感覺是先使用 `offset_date` 和 `limit` 先選定範圍，
        #      再篩選符合的 `max_id`, `min_id` 的項目，
        #      所以當 `offset_date` 不變的情況下，取得訊息的數量只會越來越少。
        #   3. `offset_date` 若傳入 `0|None`，則預設為當前時間。
        #   4. Telegram 時間為 UTC 時間。
        # 關於回傳值：
        #   https://core.telegram.org/constructor/messages.channelMessages
        #   1. `count` 為該聊天室紀錄於服務端的總訊息比數。
        #      (但可能不完全紀錄於服務端 ?! (官方說的))
        #   2. 回傳的訊息是依時間倒序排序的。
        #   3. `chats`, `users` 中包含 `messages` 所提到的對象 (ex: 轉傳的訊息對象也在裡面)
        #   4. `limit` 最多為 100 則。 (2020.11.23 紀錄)

        result = await client(telethon.functions.messages.GetHistoryRequest(
            peer = groupPeer,
            offset_id = 0,
            offset_date = theDt,
            add_offset = 0,
            limit = 1,
            max_id = 0,
            min_id = 0,
            hash = 0
        ))
        oldMsgId = result.messages[0].id if len(result.messages) > 0 else 1

        isBleak = False
        currDate = None
        currMinMsgId = 0
        userList = []
        speakerList = []
        while True:
            result = await client(telethon.functions.messages.GetHistoryRequest(
                peer = groupPeer,
                offset_id = 0,
                offset_date = currDate,
                add_offset = 0,
                limit = 100,
                max_id = currMinMsgId,
                min_id = oldMsgId,
                hash = 0
            ))
            resultType = type(result)
            if resultType == telethon.types.messages.MessagesNotModified:
                print(f'type: {resultType}, count: {result.count}')
                break
            print(
                f'type: {resultType},'
                f' count: {result.count if hasattr(result, "count") else "---"},'
                f' messages: {len(result.messages)},'
                f' chats: {len(result.chats)},'
                f' users: {len(result.users)}'
            )

            resultMessages = result.messages
            messagesLength = len(resultMessages)
            if messagesLength == 0:
                break

            resultLastMessage = resultMessages[messagesLength - 1]
            print(
                f'  {resultMessages[0].id}({resultMessages[0].date})'
                f' ~ {resultLastMessage.id}({resultLastMessage.date})'
            )

            for user in result.users:
                # 排除 自己, 已刪除帳號, 機器人
                if ynRealUser and (user.is_self or user.deleted or user.bot):
                    continue
                # 排除欲除外用戶
                if isHasExcludedUsers and user.id in excludedUserList:
                    continue
                # 排除仿用戶
                if self.lookforClientInfo(user.id) != None:
                    continue

                # 過濾已抓取的
                if user.id in userList:
                    continue

                userList.append(user.id)
                speakerList.append(user)

                if isHasAmount and len(speakerList) >= amount:
                    isBleak = True
                    break
            print(f'  get {len(result.users)} users -> {len(speakerList)}')

            if isBleak:
                break

            currDate = resultLastMessage.date
            currMinMsgId = resultLastMessage.id

        return speakerList

