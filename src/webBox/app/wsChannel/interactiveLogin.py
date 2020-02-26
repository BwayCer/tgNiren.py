#!/usr/bin/env python3


import typing
import os
import random
import telethon.sync as telethon
import utils.novice as novice
import webBox.serverMix as serverMix
from tgkream.utils import TgSession


__all__ = ['sentCode', 'verifiedCode']


TelegramClient = telethon.TelegramClient


async def sendCode(pageId: str, prop: typing.Any = None) -> dict:
    innerSession = serverMix.innerSession.get(pageId)

    if 'interactiveLogin' in innerSession:
        info = innerSession['interactiveLogin']
    else:
        info = innerSession['interactiveLogin'] = {
            'runId': random.randrange(1000000, 9999999),
            'phoneNumber': '',
            'sessionPath': '',
            'sentCode': None,
            'client': None,
        }

    if type(prop) != dict:
        return {'code': -1, 'message': '"prop" 參數必須是 `Object` 類型。'}
    if not ('phoneNumber' in prop and type(prop['phoneNumber']) == str):
        return {'code': -1, 'message': '"prop.phoneNumber" 參數不符合預期'}

    runId = info['runId']

    phoneNumber = prop['phoneNumber']
    novice.logNeedle.push('(runId: {}) login sendCode +{}'.format(runId, phoneNumber))

    # 檢查是否該仿用戶已登入
    novice.logNeedle.push('(runId: {}) test with common session path'.format(runId))
    tgSession = TgSession('telethon-' + novice.py_env['apiId'])
    sessionPath = tgSession.getSessionPath(phoneNumber)
    if os.path.exists(sessionPath):
        errInfo, client = await _checkConnectClient(runId, tgSession, phoneNumber)
        if client != None and await client.is_user_authorized():
            await _disconnectClient(info, client)
            message = '+{} 仿用戶已登入'.format(phoneNumber)
            novice.logNeedle.push('(runId: {}) {}'.format(message))
            return {'code': 1, 'message': message, 'phoneNumber': phoneNumber}

    # 使用暫時的 session 路徑進行登入
    novice.logNeedle.push('(runId: {}) login with temporary session path'.format(runId))
    tgSession = TgSession('telethon-tmpLogin-' + novice.py_env['apiId'])
    errInfo, client = await _checkConnectClient(runId, tgSession, phoneNumber)
    if errInfo != None:
        return errInfo

    info['phoneNumber'] = phoneNumber
    info['sessionPath'] = tgSession.getSessionPath(phoneNumber)
    info['client'] = client

    # 如果已登入的狀態不該存在 "tmpLogin" 前綴的路徑下
    # 所以無需測試 `client.is_user_authorized()` 方法
    try:
        # https://docs.telethon.dev/en/latest/modules/client.html#telethon.client.auth.AuthMethods.send_code_request
        novice.logNeedle.push('(runId: {}) client.send_code_request'.format(runId))
        sentCode = await client.send_code_request(phoneNumber)
        phoneCodeHash = sentCode.phone_code_hash
        novice.logNeedle.push(
            '(runId: {}) sentCode:\n'
            '  type: {}\n'
            '  phone_code_hash: {}\n'
            '  next_type: {}\n'
            '  timeout: {}'.format(
                runId,
                sentCode.type,
                phoneCodeHash,
                sentCode.next_type,
                sentCode.timeout
            )
        )
        info['sentCode'] = sentCode
    except Exception as err:
        typeName = err.__class__.__name__
        errMsg = _sendCodeKnownErrorTypeInfo[typeName] \
            if typeName in _sendCodeKnownErrorTypeInfo \
            else novice.sysTracebackException()
        novice.logNeedle.push('(runId: {}) sentCode +{} Failed {}'.format(runId, phoneNumber, errMsg))
        return {'code': -3, 'message': errMsg, 'phoneNumber': phoneNumber}

    novice.logNeedle.push('(runId: {}) 請查收驗證碼'.format(runId))
    return {
        'code': 2,
        'message': '請查收驗證碼。',
        'phoneNumber': phoneNumber,
        'phoneCodeHash': phoneCodeHash,
    }

async def verifiedCode(pageId: str, prop: typing.Any = None) -> dict:
    innerSession = serverMix.innerSession.get(pageId)
    if not 'interactiveLogin' in innerSession:
        return {'code': -1, 'message': '沒有待登入的用戶。'}

    if type(prop) != dict:
        return {'code': -1, 'message': '"prop" 參數必須是 `Object` 類型。'}
    if not ('phoneNumber' in prop and type(prop['phoneNumber']) == str):
        return {'code': -1, 'message': '"prop.phoneNumber" 參數不符合預期'}
    if not ('phoneCodeHash' in prop and type(prop['phoneCodeHash']) == str):
        return {'code': -1, 'message': '"prop.phoneCodeHash" 參數不符合預期'}
    if not ('verifiedCode' in prop and type(prop['verifiedCode']) == str):
        return {'code': -1, 'message': '"prop.verifiedCode" 參數不符合預期'}

    info = innerSession['interactiveLogin']
    runId = info['runId']
    sessionPath = info['sessionPath']
    sentCode = info['sentCode']
    client = info['client']

    phoneNumber = prop['phoneNumber']
    phoneCodeHash = prop['phoneCodeHash']
    verifiedCode = prop['verifiedCode']

    if phoneNumber != info['phoneNumber'] \
            and phoneCodeHash != info['sentCode'].phone_code_hash:
        errMsg = '登入的仿用戶 +{} 與主機留存仿用戶 +{} 不相同'.format(
            phoneNumber, info['phoneNumber']
        )
        novice.logNeedle.push('(runId: {}) {}'.format(runId, errMsg))
        return {
            'code': -2,
            'message': errMsg,
            'phoneNumber': info['phoneNumber'],
            'anotherPhoneNumber': phoneNumber,
        }

    novice.logNeedle.push(
        '(runId: {}) login +{} with {} phoneCodeHash and {} verifiedCode'.format(
            runId, phoneNumber, phoneCodeHash, phoneNumber
        )
    )
    try:
        await client.sign_in(phoneNumber, verifiedCode, phone_code_hash = phoneCodeHash)
        message = '+{} 仿用戶登入成功'.format(phoneNumber)
        novice.logNeedle.push('(runId: {}) {}'.format(runId, message))

        await _disconnectClient(info, client)
        _mvSessionPath(sessionPath, phoneNumber, 'telethon-' + novice.py_env['apiId'])
        novice.logNeedle.push('(runId: {}) disconnect & mv finish'.format(runId))

        return {'code': 3, 'message': message, 'phoneNumber': phoneNumber}
    except Exception as err:
        typeName = err.__class__.__name__
        errMsg = _signInKnownErrorTypeInfo[typeName] \
            if typeName in _signInKnownErrorTypeInfo \
            else novice.sysTracebackException()
        novice.logNeedle.push('(runId: {}) login +{} Failed {}'.format(runId, phoneNumber, errMsg))
        return {'code': -3, 'message': errMsg, 'phoneNumber': phoneNumber}


_sendCodeKnownErrorTypeInfo = {
    'ApiIdInvalidError': 'api_id/api_hash 組合無效。',
    'ApiIdPublishedFloodError': '該 API ID 已發佈在某個地方，您現在無法使用。',
    'AuthRestartError': '重新啟動授權過程。',
    'InputRequestTooLongError':
        '輸入的請求太長。這可能是庫中的錯誤，因為當序列化的字節數超過其應有的字節數時（例如，在消息末尾附加向量構造函數代碼），可能會發生此錯誤。',
    'PhoneNumberAppSignupForbiddenError': 'PhoneNumberAppSignupForbiddenError',
    'PhoneNumberBannedError': '已使用的電話號碼已被電報禁止，無法再使用。也許檢查 https://www.telegram.org/faq_spam。',
    'PhoneNumberFloodError': '您要求輸入代碼的次數過多。',
    'PhoneNumberInvalidError': '電話號碼是無效的。',
    'PhonePasswordFloodError': '您嘗試登錄太多次了。',
    'PhonePasswordProtectedError': '此電話受密碼保護。',
}
_signInKnownErrorTypeInfo = {
    'PhoneCodeEmptyError': '電話代碼丟失。',
    'PhoneCodeExpiredError': '確認碼已過期。',
    'PhoneCodeInvalidError': '輸入的電話代碼無效。',
    'PhoneNumberInvalidError': '電話號碼是無效的。',
    'PhoneNumberUnoccupiedError': '電話號碼尚未使用。',
    'SessionPasswordNeededError': '啟用了兩步驗證，並且需要密碼。',
}

async def _checkConnectClient(
        runId: int,
        tgSession: TgSession,
        phoneNumber: str
        ) -> typing.Tuple[typing.Union[None, dict], typing.Union[None, TelegramClient]]:
    client = TelegramClient(
        tgSession.getSessionPath(phoneNumber, noExt = True),
        novice.py_env['apiId'],
        novice.py_env['apiHash']
    )

    try:
        novice.logNeedle.push('(runId: {}) client.connect'.format(runId))
        await client.connect()
    except telethon.errors.PhoneNumberBannedError as err:
        errMsg = 'The phone {} is Banned.'.format(phoneNumber)
        novice.logNeedle.push('(runId: {}) PhoneNumberBannedError: {}'.format(runId, errMsg))
        _mvSessionPath(sessionPath, phoneNumber, 'telethon-banned-' + novice.py_env['apiId'])
        return (
            {'code': -3, 'message': errMsg, 'phoneNumber': phoneNumber},
            None
        )
    except Exception as err:
        errMsg = novice.sysTracebackException()
        novice.logNeedle.push('(runId: {}) {}'.format(runId, errMsg))
        _mvSessionPath(sessionPath, phoneNumber, 'telethon-rm-' + novice.py_env['apiId'])
        return (
            {'code': -3, 'message': errMsg, 'phoneNumber': phoneNumber},
            None
        )

    return (None, client)

async def _disconnectClient(info: dict, client: TelegramClient) -> None:
    await client.disconnect()
    info['phoneNumber'] = ''
    info['sessionPath'] = ''
    info['sentCode'] = None
    info['client'] = None

def _mvSessionPath(origSessionPath: str, phoneNumber: str, newSessionPrifix: str) -> None:
    tgSession = TgSession(newSessionPrifix)
    sessionPath = tgSession.getSessionPath(phoneNumber)
    os.rename(origSessionPath, sessionPath)

