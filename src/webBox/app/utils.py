#!/usr/bin/env python3


import typing
import asyncio
import utils.novice as novice
from tgkream.tgTool import TgDefaultInit, TgBaseTool


__all__ = ['console', 'getTgTool', 'getNiUsersStatusInfo']


class console():
    baseMsg = {
        '_undefined': 'Unexpected log message.',
        '_undefinedError': 'Unexpected error message.',
        '_illegalInvocation': 'Illegal invocation.',
        '_notExpectedType': '"{}" is not of the expected type.',
        '_restrictedType': '"{}" must be a `{}` type.',
        # https://docs.telethon.dev/en/latest/concepts/errors.html
        'commonErrors_floodWait': 'Too many requests and wait {} seconds.',
        'commonErrors_FloodWaitError':
            'The +{} phone was blocked until {} seconds later because of "FloodWaitError".',
        'commonErrors_PeerFloodError':
            'The +{} phone was blocked until 12 hours later because of "PeerFloodError".',
    }

    def logMsg(runIdCode: str, msg: str) -> str:
        novice.logNeedle.push('(runId: {}) log {}'.format(runIdCode, msg))
        return msg

    def errorMsg(runIdCode: str, msg: str) -> str:
        novice.logNeedle.push('(runId: {}) error {}'.format(runIdCode, msg))
        return msg

    def catchErrorMsg(runIdCode: str, methodName: str, errMsg: str) -> str:
        novice.logNeedle.push(
            '(runId: {}) from {} Failed {}'.format(runIdCode, methodName, errMsg)
        )
        return errMsg

    def _getMsg(msgTypeInfos: dict, typeName: str, defaultMsg: str, *args) -> str:
        if typeName in msgTypeInfos:
            msg = msgTypeInfos[typeName]
            if len(args) > 0:
                msg = msg.format(*args)
        else:
            msg = '{} (type: {})'.format(defaultMsg, typeName)
        return msg

    def getMsg(msgTypeInfos: dict, typeName: str, *args) -> str:
        return console._getMsg(
            msgTypeInfos, typeName,
            console.baseMsg['_undefined'],
            *args
        )

    def getErrorMsg(msgTypeInfos: dict, typeName: str, *args) -> str:
        return console._getMsg(
            msgTypeInfos, typeName,
            console.baseMsg['_undefinedError'],
            *args
        )

    def log(runIdCode: str, msgTypeInfos: dict, typeName: str, *args) -> str:
        msg = console._getMsg(
            msgTypeInfos, typeName,
            console.baseMsg['_undefined'],
            *args
        )
        novice.logNeedle.push('(runId: {}) log {}'.format(runIdCode, msg))
        return msg

    def error(runIdCode: str, msgTypeInfos: dict, typeName: str, *args) -> str:
        msg = console._getMsg(
            msgTypeInfos, typeName,
            console.baseMsg['_undefinedError'],
            *args
        )
        novice.logNeedle.push('(runId: {}) error {}'.format(runIdCode, msg))
        return msg

    def catchError(
            runIdCode: str,
            methodName: str,
            errorTypeInfos: typing.Union[None, dict] = None,
            typeName: str = '',
            *args) -> str:
        if errorTypeInfos != None and typeName in errorTypeInfos:
            errMsg = errorTypeInfos[typeName]
            if len(args) > 0:
                errMsg = errMsg.format(*args)
        else:
            errMsg = novice.sysTracebackException()
        novice.logNeedle.push(
            '(runId: {}) from {} Failed {}'.format(runIdCode, methodName, errMsg)
        )
        return errMsg


def getTgTool(clientCount: int = 0) -> TgBaseTool:
    tgTool = TgDefaultInit(
        TgBaseTool,
        clientCount = clientCount if clientCount > 0 else 3,
        papaPhone = novice.py_env['papaPhoneNumber']
    )
    return tgTool


_getNiUsersStatusInfo_task = None

async def _getNiUsersStatusInfo_handle():
    tgTool = TgDefaultInit(
        TgBaseTool,
        clientCount = 1,
        papaPhone = novice.py_env['papaPhoneNumber']
    )

    chanDataNiUsers = tgTool.chanDataNiUsers
    usablePhones = chanDataNiUsers.getUsablePhones()
    niUsers = chanDataNiUsers.chanData.data['niUsers']
    bandPhones = niUsers['bandList']
    lockPhones = niUsers['lockList']

    # NOTE:
    # 原本打算以下述程式碼來優化加快檢查時程，
    # 但卻會因為記憶體不足而以退出代碼 137 退出程式。
    #     async def _getNiUsersStatusInfo_runLogin(tgTool: TgBaseTool, phoneNumber: str):
    #         client = await tgTool.login(phoneNumber)
    #         if client != None:
    #             await tgTool.release(phoneNumber)
    #
    #     runLoginTasks = []
    #     for phoneNumber in usablePhones:
    #         runLoginTasks.append(_getNiUsersStatusInfo_runLogin(tgTool, phoneNumber))
    #
    #     await asyncio.gather(*runLoginTasks)
    for phoneNumber in usablePhones:
        if novice.indexOf(bandPhones, phoneNumber) != -1 \
                or novice.indexOf(lockPhones, phoneNumber) != -1:
            continue

        novice.logNeedle.push(f'test {phoneNumber}')
        client = await tgTool.login(phoneNumber)
        if client != None:
            await tgTool.release(phoneNumber)
        novice.logNeedle.push(f'test {phoneNumber} OK')

    allCount = len(chanDataNiUsers.getUsablePhones())
    lockCount = len(bandPhones) + len(lockPhones)
    return {
        'allCount': allCount,
        'lockCount': lockCount,
        'usableCount': allCount - lockCount,
    }

async def getNiUsersStatusInfo():
    global _getNiUsersStatusInfo_task
    task = _getNiUsersStatusInfo_task
    if task == None or task.done():
        task = _getNiUsersStatusInfo_task \
            = asyncio.create_task(_getNiUsersStatusInfo_handle())

    return await asyncio.wrap_future(task)

