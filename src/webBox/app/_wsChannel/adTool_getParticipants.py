#!/usr/bin/env python3


import typing
import os
import random
import utils.novice as novice
import webBox.serverMix as serverMix
from tgkream.tgTool import telethon, TgDefaultInit, TgBaseTool
import webBox.app.tgToolUtils as tgToolUtils


__all__ = ['getParticipants']


async def getParticipants(pageId: str, prop: typing.Any = None) -> dict:
    innerSession = serverMix.innerSession.get(pageId)
    if innerSession['runing']:
        return {
            'code': -1,
            'message': '工具執行中。',
        }

    if type(prop) != dict:
        return {
            'code': -1,
            'messageType': '_restrictedType',
            'message': _getMessage.logNotRecord(
                _getMessage.baseMsg, '_restrictedType', 'prop', 'Object'
            )
        }
    if not ('groupPeer' in prop and type(prop['groupPeer']) == str):
        return {
            'code': -1,
            'messageType': '_notExpectedType',
            'message': _getMessage.logNotRecord(
                _getMessage.baseMsg, '_notExpectedType', 'prop.groupPeer'
            )
        }

    groupPeer = prop['groupPeer']

    # 用於打印日誌
    runId = random.randrange(1000000, 9999999)

    novice.logNeedle.push(
        '(runId: {}) {}'.format(runId, 'adTool.getParticipants 初始化...')
    )
    try:
        tgTool = tgToolUtils.getTgTool(1)
        await tgTool.init()
    except Exception as err:
        errTypeName = err.__class__.__name__
        return {
            'code': -1,
            'messageType': errTypeName,
            'message': _getMessage.catchError(runId, 'init TgTool', {}, errTypeName),
        }

    clientInfo = tgTool.pickClient()
    myId = clientInfo['id']
    client = clientInfo['client']

    novice.logNeedle.push(
        '(runId: {}) tgTool.joinGroup() {} join {}'.format(runId, myId, groupPeer)
    )

    _, isPrivate = telethon.utils.parse_username(groupPeer)
    if isPrivate:
        try:
            await tgTool.joinGroup(client, groupPeer)
        except telethon.errors.UserAlreadyParticipantError as err:
            # 已經是聊天的參與者。 (私有聊天室)
            pass
        except Exception as err:
            await tgTool.release()

            errTypeName = err.__class__.__name__
            return {
                'code': -1,
                'messageType': errTypeName,
                'message': _getMessage.catchError(
                    runId,
                    'tgTool.joinGroup()',
                    _joinGroupKnownErrorTypeInfo,
                    errTypeName
                ),
            }

    novice.logNeedle.push(
        '(runId: {}) tgTool.getParticipants()'.format(runId)
    )
    try:
        _, users = await tgTool.getParticipants(client, groupPeer)
        userIds = []
        for user in users:
            username = user.username
            if username == None:
                continue
            userIds.append(user.username)
    except Exception as err:
        await tgTool.release()

        errTypeName = err.__class__.__name__
        return {
            'code': -1,
            'messageType': errTypeName,
            'message': _getMessage.catchError(
                runId,
                'tgTool.getParticipants()',
                _getParticipantsKnownErrorTypeInfo,
                errTypeName
            ),
        }

    await tgTool.release()

    return {
        'code': 1,
        'messageType': 'success',
        'message': _getMessage.log(
            runId, _interactiveMessage, 'success', len(userIds)
        ),
        'participantIds': userIds,
    }


_interactiveMessage = {
    # -1 錯誤
    # 1 成功
    'success': '成功拿到 {} 個用戶名。',
}
_joinGroupKnownErrorTypeInfo = {
    'ChannelsTooMuchError': '您加入了太多的頻道/超級群組。',
    'ChannelInvalidError': '無效的頻道對象。',
    'ChannelPrivateError': '您無法加入私人的頻道/超級群組。另一個原因可能是您被禁止了。',
    'InviteHashEmptyError': '邀請連結丟失。 (私有聊天室)',
    'InviteHashExpiredError': '邀請連結已過期。 (私有聊天室)',
    'InviteHashInvalidError': '無效的邀請連結。 (私有聊天室)',
    'SessionPasswordNeededError': '啟用了兩步驗證，並且需要密碼。 (私有聊天室)(登入錯誤?)',
    'UsersTooMuchError': '超過了最大用戶數 (ex: 創建聊天)。 (私有聊天室)',
    'UserAlreadyParticipantError': '已經是聊天的參與者。 (私有聊天室)',
    # 只有在 https://core.telegram.org/method/messages.importChatInvite 的錯誤
    # 400 MSG_ID_INVALID
    # 400 PEER_ID_INVALID
    # 只有在 https://core.telegram.org/method/channels.JoinChannel 的錯誤
    # 400 INVITE_HASH_EMPTY
    # 400 INVITE_HASH_EXPIRED
    # 400 INVITE_HASH_INVALID
    # 400 MSG_ID_INVALID
    # 400 PEER_ID_INVALID
    # 400 USERS_TOO_MUCH
    # 400 USER_ALREADY_PARTICIPANT
    # 400 USER_CHANNELS_TOO_MUCH
}
_getParticipantsKnownErrorTypeInfo = {
    'ChannelInvalidError': '無效的頻道對象。',
    'ChannelPrivateError': '您無法加入私人的頻道/超級群組。另一個原因可能是您被禁止了。',
    'ChatAdminRequiredError': '您沒有執行此操作的權限。',
    'InputConstructorInvalidError': '提供的構造函數無效。 (*程式錯誤)',
    # 只在 https://tl.telethon.dev/methods/channels/get_participants.html 的錯誤
    'TimeoutError': '從工作程序中獲取數據時發生超時。 (*程式錯誤)',
}

class _getMessage():
    baseMsg = {
        '_undefined': 'Unexpected log message.',
        '_undefinedError': 'Unexpected error message.',
        '_illegalInvocation': 'Illegal invocation.',
        '_notExpectedType': '"{}" is not of the expected type.',
        '_restrictedType': '"{}" must be a `{}` type.',
    }

    def logNotRecord(msgTypeInfos: dict, typeName: str, *args) -> str:
        if typeName in msgTypeInfos:
            msg = msgTypeInfos[typeName]
            if len(args) > 0:
                msg = msg.format(*args)
        else:
            msg = '{} (type: {})'.format(
                _getMessage.baseMsg['_undefined'],
                typeName
            )
        return msg

    def log(runIdCode: str, msgTypeInfos: dict, typeName: str, *args) -> str:
        if typeName in msgTypeInfos:
            msg = msgTypeInfos[typeName]
            if len(args) > 0:
                msg = msg.format(*args)
        else:
            msg = '{} (type: {})'.format(
                _getMessage.baseMsg['_undefined'],
                typeName
            )
        novice.logNeedle.push('(runId: {}) log {}'.format(runIdCode, msg))
        return msg

    def error(runIdCode: str, msgTypeInfos: dict, typeName: str, *args) -> str:
        if typeName in msgTypeInfos:
            msg = msgTypeInfos[typeName]
            if len(args) > 0:
                msg = msg.format(*args)
        else:
            msg = '{} (type: {})'.format(
                _getMessage.baseMsg['_undefinedError'],
                typeName
            )
        novice.logNeedle.push('(runId: {}) error {}'.format(runIdCode, msg))
        return msg

    def catchError(
            runIdCode: str,
            fromState: str,
            errorTypeInfos: dict,
            typeName: str) -> str:
        errMsg = errorTypeInfos[typeName] \
            if typeName in errorTypeInfos \
            else novice.sysTracebackException()
        novice.logNeedle.push(
            '(runId: {}) from {} Failed {}'.format(runIdCode, fromState, errMsg)
        )
        return errMsg

