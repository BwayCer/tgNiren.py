#!/usr/bin/env python3


from typing import Union
import os
from telethon.sync import TelegramClient


__all__ = ['TgLoginTool']


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

