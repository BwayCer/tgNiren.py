#!/usr/bin/env python3


import typing
import json
import re
import asyncio
import importlib
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
            _InnerSession_expiredCheckLoop(innerSession)
        elif toolName == 'WsHouse':
            global wsHouse
            wsHouse = _WsHouse()
        else:
            raise Exception('Not found "{}" in serverMix Tool'.format(toolName))


class _InnerSession():
    def __init__(self, extensionHours: float = 0.06):
        self._cache = novice.CacheData(extensionHours = extensionHours)

    def open(self, pageSession: dict) -> str:
        _cache = self._cache
        pageId = _cache.register(data = {'data': pageSession})
        return pageId

    def hasPageId(self, pageId: typing.Union[None, str]) -> bool:
        return False if pageId == None else self._cache.has(pageId)

    def extendedDuration(self, pageId: str):
        self._cache.extendedDuration(pageId)

    def get(self, pageId: str) -> typing.Union[None, dict]:
        _cache = self._cache
        if not _cache.has(pageId):
            return None

        _cache.extendedDuration(pageId)
        return _cache.get(pageId)['data']

def _InnerSession_expiredCheckLoop(innerSession: _InnerSession):
    @novice.dSetTimeout(intervalSec = 3600 * 3 * 0.01)
    def expiredCheck():
        _cache = innerSession._cache
        if _cache.size() == 0:
            return

        expiredList = _cache.expiredCheck()
        for expiredItem in expiredList:
            pageId = expiredItem['key']
            novice.logNeedle.push(
                f'store rm pageId: {pageId};'
                f' isHasInWsHouse: {wsHouse.roomCache.has(pageId)}'
            )


class _WsHouse():
    def __init__(self, extensionHours: float = 0.02):
        self.channelCache = novice.CacheData(extensionHours = extensionHours)
        self.roomCache = novice.CacheData()

    def addChannel(self,
            task: asyncio.Task,
            pageId: str,
            socket: quart.wrappers.Websocket) -> str:
        key = self.channelCache.register(data = {
            'task': task,
            'pageId': pageId,
            'socket': socket,
            'rooms': [pageId],
        })

        if not self.roomCache.has(pageId):
            self.roomCache.register(key = pageId, data = {'channels': []})
        roomData = self.roomCache.get(pageId)
        roomData['channels'].append(key)

        return key

    def removeChannel(self, key: str):
        if not self.channelCache.has(key):
            return

        channelData = self.channelCache.get(key)
        for roomId in channelData['rooms']:
            if not self.roomCache.has(roomId):
                continue
            roomData = self.roomCache.get(roomId)
            channels = roomData['channels']
            if key in channels:
                channels.remove(key)
                if len(channels) == 0:
                    self.roomCache.remove(roomId)

        self.channelCache.remove(key)

    def channelExtendedDuration(self, key: str):
        self.channelCache.extendedDuration(key)

    def hasRoom(self, key: str) -> bool:
        return self.channelCache.has(key) or self.roomCache.has(key)

    async def send(self,
            room: typing.Union[str, list],
            stateCode: int = 200,
            payload: typing.Union[None, dict] = None,
            rtns: typing.Union[None, list] = None,
            fnResult: typing.Union[None, dict] = None):
        if payload == None:
            payload = {}

        channelCache = self.channelCache
        roomCache = self.roomCache

        rooms = [room] if type(room) == str else room
        if not 'stateCode' in payload:
            payload['stateCode'] = stateCode
        if fnResult != None:
            payload['rtns'] = [fnResult]
        elif rtns != None:
            payload['rtns'] = rtns

        for roomkey in rooms:
            newPayload = payload.copy()

            try:
                if channelCache.has(roomkey):
                    cacheData = channelCache.get(roomkey)
                    newPayload['wsId'] = roomkey
                    await cacheData['socket'].send(json.dumps(newPayload))
                elif roomCache.has(roomkey):
                    roomData = self.roomCache.get(roomkey)
                    channels = roomData['channels']
                    for channelKey in channels:
                        if channelCache.has(channelKey):
                            cacheData = channelCache.get(channelKey)
                            newPayload['wsId'] = channelKey
                            await cacheData['socket'].send(json.dumps(newPayload))
            except Exception as err:
                novice.logNeedle.push(
                    'from serverMix/send: {} Failed {}'.format(
                        roomkey,
                        novice.sysTracebackException()
                    )
                )

class _WsHouse2():
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
            if len(connectedSockets) > 1:
                connectedSockets.remove(socket)
            else:
                del house[roomName]

    def connectLength(self, roomName: str) -> None:
        house = self.house
        return len(house[roomName]) if roomName in house else 0

    async def send(self, roomName: str, payload: typing.Any) -> None:
        house = self.house
        if roomName in house:
            for socket in house[roomName]:
                await socket.send(payload)

