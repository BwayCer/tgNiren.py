#!/usr/bin/env python3


import typing
import re
import importlib
import uuid
# https://pgjones.gitlab.io/quart/source/quart.static.html
import quart
import utils.novice as novice


__all__ = ['Router', 'enableTool', 'innerSession', 'wsHouse']


innerSession = None
wsHouse = None


class Router():
    def __init__(self, app: quart.Quart, controllerDirPath: str = ''):
        self._app = app
        self._controllerDirPath \
            = controllerDirPath + '.' if controllerDirPath != '' else ''

    _regexControllerPath = r'^(.*)\.([^.]*)$'

    def require(self, controllerPath: str) -> typing.Tuple[typing.Callable, str]:
        filePath = self._controllerDirPath + controllerPath
        matchControllerPath = re.search(self._regexControllerPath, filePath)
        pyFilePath = matchControllerPath.group(1)
        methodName = matchControllerPath.group(2)
        action = getattr(importlib.import_module(pyFilePath), methodName)
        return action, filePath

    # GET, POST, HEAD, PUT, PATCH, DELETE
    def add(self,
            method: str,
            url: str,
            controllerPath: str,
            *args, **kwargs) -> None:
        action, filePath = self.require(controllerPath)
        self._app.add_url_rule(
            url, filePath, action,
            *args,
            methods = [method],
            **kwargs
        )

    def websocket(self, url: str, controllerPath: str, *args, **kwargs) -> None:
        action, filePath = self.require(controllerPath)
        self._app.add_websocket(url, filePath, action, *args, **kwargs)


def enableTool(*args):
    for toolName in args:
        if toolName == 'InnerSession':
            global innerSession
            innerSession = _InnerSession()
        elif toolName == 'WsHouse':
            global wsHouse
            wsHouse = _WsHouse()
        else:
            raise Exception('Not found "{}" in serverMix Tool'.format(toolName))


class _InnerSession():
    def __init__(self, extensionHours: str = 4):
        self._data = {}
        self._extensionHours = extensionHours

    # TODO 看能不能改成計時器執行
    def _expiredCheck(self) -> None:
        sessionData = self._data
        nowTimeMs = novice.dateNowTimestamp()
        for key in list(sessionData):
            pageData = sessionData[key]
            if pageData['expiryTimestamp'] < nowTimeMs:
                del sessionData[key]

    def _getNewId(self) -> str:
        sessionData = self._data
        while True:
            idTxt = str(uuid.uuid4())
            if not idTxt in sessionData:
                break
        return idTxt

    def open(self, pageSession: dict) -> str:
        self._expiredCheck()
        pageId = self._getNewId()
        expiryDate = novice.dateNowAfter(hours = self._extensionHours)
        self._data[pageId] = {
            'expiryTimestamp': novice.dateTimestamp(expiryDate),
            'data': pageSession,
        }
        return pageId

    def hasPageId(self, pageId: typing.Union[None, str]) -> bool:
        return False if pageId == None else pageId in self._data

    def get(self, pageId: str) -> typing.Union[None, dict]:
        sessionData = self._data
        if pageId in sessionData:
            pageData = sessionData[pageId]
            expiryDate = novice.dateNowAfter(hours = self._extensionHours)
            pageData['expiryTimestamp'] = novice.dateTimestamp(expiryDate)
            return pageData['data']

        return None


class _WsHouse():
    def __init__(self):
        self.house = {}

    def open(self, roomName: str, socket) -> None:
        house = self.house
        if roomName in house:
            connectedSockets = house[roomName]
        else:
            connectedSockets = house[roomName] = set()
        connectedSockets.add(socket)

    def close(self, roomName: str, socket) -> None:
        house = self.house
        if roomName in house:
            connectedSockets = house[roomName]
            connectedSockets.remove(socket)

    async def send(self, roomName: str, payload: typing.Any) -> None:
        house = self.house
        if roomName in house:
            for socket in house[roomName]:
                await socket.send(payload)

