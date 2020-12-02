#!/usr/bin/env python3


import typing
import os
import datetime
import re
import random
import asyncio
import base64
import telethon.sync as telethon
import utils.novice as novice
import webBox.serverMix as serverMix
from tgkream.utils import TgSession
from webBox.app._wsChannel.niUsersStatus import updateStatus as niUsersStatusUpdateStatus


__all__ = ['login', 'sendCode', 'verifiedCode', 'verifiedPassword', 'deleteAccount', 'signup']


TelegramClient = telethon.TelegramClient
tgSession = TgSession('telethon-' + str(novice.py_env['apiId']))


async def login(pageId: str, wsId: str, prop: typing.Any = None) -> dict:
    if type(prop) != dict:
        return {
            'code': -1,
            'messageType': '_restrictedType',
            'message': _getMessage.logNotRecord(
                _interactiveLoginMessage, '_restrictedType', 'prop', 'Object'
            ),
        }
    if not ('phoneNumber' in prop and type(prop['phoneNumber']) == str):
        return {
            'code': -1,
            'messageType': '_notExpectedType',
            'message': _getMessage.logNotRecord(
                _interactiveLoginMessage, '_notExpectedType', 'prop.phoneNumber'
            ),
        }

    phoneNumber = prop['phoneNumber']
    _, runIdCode, info = _checkSession(pageId, 'login', phoneNumber, '')

    # 上個號碼都未成功時卻開始登入下一個號碼
    if info['client'] != None and info['phoneNumber'] != phoneNumber:
        novice.logNeedle.push(
            '(runId: {}) remove last login +{}'.format(runIdCode, info['phoneNumber'])
        )
        _mvSessionPath(
            runIdCode,
            info['phoneNumber'],
            fromAddPrifix = 'tmpLogin',
            toAddPrifix = 'rm'
        )
        await _disconnectClient(runIdCode, info, info['client'])

    # 檢查是否該仿用戶已登入
    novice.logNeedle.push('(runId: {}) test with common session path'.format(runIdCode))
    if os.path.exists(tgSession.getSessionPath(phoneNumber)):
        errInfo, client = await _checkConnectClient(runIdCode, '', phoneNumber)
        if client != None and await client.is_user_authorized():
            await _disconnectClient(runIdCode, info, client)
            await niUsersStatusUpdateStatus(allCount = 1, usableCount = 1)
            return {
                'code': 4,
                'messageType': 'loggedin',
                'message': _getMessage.log(
                    runIdCode, _interactiveLoginMessage, 'loggedin', phoneNumber
                ),
                'phoneNumber': phoneNumber,
            }
        else:
            # 重新跑登入流程
            _mvSessionPath(
                runIdCode,
                phoneNumber,
                toAddPrifix = 'tmpLogin'
            )

    # 使用暫時的 session 路徑進行登入
    novice.logNeedle.push(
        '(runId: {}) login with temporary session path'.format(runIdCode)
    )
    errInfo, client = await _checkConnectClient(runIdCode, 'tmpLogin', phoneNumber)
    if errInfo != None:
        return errInfo

    info['phoneNumber'] = phoneNumber
    info['client'] = client

    # 如果已登入的狀態不該存在 "tmpLogin" 前綴的路徑下
    # 所以無需測試 `client.is_user_authorized()` 方法
    errInfo, sendCodeInfo = await _sendCode(runIdCode, client, phoneNumber)
    if errInfo != None:
        return errInfo
    else:
        info['phoneCodeHash'] = sendCodeInfo['phoneCodeHash']
        return sendCodeInfo

async def qrLogin(pageId: str, wsId: str, prop: typing.Any = None) -> dict:
    if type(prop) != dict:
        return {
            'code': -1,
            'messageType': '_restrictedType',
            'message': _getMessage.logNotRecord(
                _interactiveLoginMessage, '_restrictedType', 'prop', 'Object'
            ),
        }
    if not ('phoneNumber' in prop and type(prop['phoneNumber']) == str):
        return {
            'code': -1,
            'messageType': '_notExpectedType',
            'message': _getMessage.logNotRecord(
                _interactiveLoginMessage, '_notExpectedType', 'prop.phoneNumber'
            ),
        }
    if not ('phoneCodeHash' in prop and type(prop['phoneCodeHash']) == str):
        return {
            'code': -1,
            'messageType': '_notExpectedType',
            'message': _getMessage.logNotRecord(
                _interactiveLoginMessage, '_notExpectedType', 'prop.phoneCodeHash'
            ),
        }

    errInfo, runIdCode, info = _checkSession(
        pageId, 'qrLogin', prop['phoneNumber'], prop['phoneCodeHash']
    )
    if errInfo != None:
        return errInfo

    if info['isQrLogin']:
        nowDt = datetime.datetime.utcnow().replace(
            tzinfo=datetime.timezone.utc
        )
        return {
            'code': 5,
            'messageType': 'qrTrying',
            'message': _getMessage.log(
                runIdCode, _interactiveLoginMessage, 'qrTrying',
                int(info['qrExpiresDt'].timestamp() - nowDt.timestamp()) \
                    if info['qrExpiresDt'] != None else '---'
            ),
        }

    info['isQrLogin'] = True
    info['qrExpiresDt'] = None

    asyncio.ensure_future(_qrLoginAction(pageId, runIdCode, info))
    return {
        'code': 5,
        'messageType': 'qrRequestReceived',
        'message': _getMessage.log(
            runIdCode, _interactiveLoginMessage, 'qrRequestReceived'
        ),
    }

async def _qrLoginAction(pageId: str, runIdCode: str, info: dict):
    phoneNumber = info['phoneNumber']
    client = info['client']

    novice.logNeedle.push(
        '(runId: {}) client(auth.ExportLoginTokenRequest()) +{} use QRcode Login'.format(
            runIdCode, phoneNumber
        )
    )
    try:
        exportLoginTokenResult = await client(
            telethon.functions.auth.ExportLoginTokenRequest(
                api_id = novice.py_env['apiId'],
                api_hash = novice.py_env['apiHash'],
                except_ids = []
            )
        )
    except Exception as err:
        info['isQrLogin'] = False

        errTypeName = err.__class__.__name__
        await serverMix.wsHouse.send(pageId, fnResult = {
            'name': 'interactiveLogin.qrLogin',
            'result': {
                'code': -3,
                'messageType': errTypeName,
                'message': _getMessage.catchError(
                    runIdCode,
                    'client(auth.ExportLoginTokenRequest())',
                    {},
                    errTypeName
                ),
            },
        })

    successLoginType = ''
    exportLoginTokenResultType = type(exportLoginTokenResult)
    if exportLoginTokenResultType == telethon.types.auth.LoginToken:
        nowDt = datetime.datetime.utcnow().replace(
            tzinfo=datetime.timezone.utc
        )
        expiresDt = exportLoginTokenResult.expires
        info['qrExpiresDt'] = expiresDt
        expiresSec = int(expiresDt.timestamp() - nowDt.timestamp())
        novice.logNeedle.push(
            '(runId: {}) get QRcode Token and after {} second expires'.format(
                runIdCode, expiresSec
            )
        )

        token = base64.b64encode(exportLoginTokenResult.token).decode()
        await serverMix.wsHouse.send(pageId, fnResult = {
            'name': 'interactiveLogin.qrLogin',
            'result': {
                'code': 5,
                'messageType': 'qrToken',
                'message': _getMessage.log(
                    runIdCode, _interactiveLoginMessage, 'qrToken', expiresSec
                ),
                'token': f'tg://login?token={token}',
                'expires': int(expiresDt.timestamp() * 1000),
            },
        })

        await asyncio.sleep(expiresSec)
        try:
            exportLoginTokenResult = await client(
                telethon.functions.auth.ExportLoginTokenRequest(
                    api_id = novice.py_env['apiId'],
                    api_hash = novice.py_env['apiHash'],
                    except_ids = []
                )
            )
        except Exception as err:
            info['isQrLogin'] = False
            await serverMix.wsHouse.send(pageId, fnResult = {
                'name': 'interactiveLogin.qrLogin',
                'result': {
                    'code': 5,
                    'messageType': 'qrTokenExpired',
                    'message': _getMessage.log(
                        runIdCode, _interactiveLoginMessage, 'qrTokenExpired'
                    ),
                },
            })

        if type(exportLoginTokenResult) == telethon.types.auth.LoginTokenSuccess:
            successLoginType = 'successLogin'
        else:
            info['isQrLogin'] = False
            await serverMix.wsHouse.send(pageId, fnResult = {
                'name': 'interactiveLogin.qrLogin',
                'result': {
                    'code': 5,
                    'messageType': 'qrTokenExpired',
                    'message': _getMessage.log(
                        runIdCode, _interactiveLoginMessage, 'qrTokenExpired'
                    ),
                },
            })
    elif exportLoginTokenResultType == telethon.types.auth.LoginTokenSuccess:
        successLoginType = 'loggedin'
    else:
        info['isQrLogin'] = False
        await serverMix.wsHouse.send(pageId, fnResult = {
            'name': 'interactiveLogin.qrLogin',
            'result': {
                'code': -2,
                'messageType': 'qrUnknownType',
                'message': _getMessage.log(
                    runIdCode, _interactiveLoginMessage, 'qrUnknownType',
                    exportLoginTokenResultType.__name__
                ),
            },
        })

    if successLoginType != '':
        info['isQrLogin'] = False

        _mvSessionPath(runIdCode, info['phoneNumber'], fromAddPrifix = 'tmpLogin')
        await _disconnectClient(runIdCode, info, client)

        await niUsersStatusUpdateStatus(allCount = 1, usableCount = 1)
        await serverMix.wsHouse.send(pageId, fnResult = {
            'name': 'interactiveLogin.qrLogin',
            'result': {
                'code': 4,
                'messageType': successLoginType,
                'message': _getMessage.log(
                    runIdCode, _interactiveLoginMessage, successLoginType, phoneNumber
                ),
                'phoneNumber': phoneNumber,
            },
        })

async def sendCode(pageId: str, wsId: str, prop: typing.Any = None) -> dict:
    if type(prop) != dict:
        return {
            'code': -1,
            'messageType': '_restrictedType',
            'message': _getMessage.logNotRecord(
                _interactiveLoginMessage, '_restrictedType', 'prop', 'Object'
            ),
        }
    if not ('phoneNumber' in prop and type(prop['phoneNumber']) == str):
        return {
            'code': -1,
            'messageType': '_notExpectedType',
            'message': _getMessage.logNotRecord(
                _interactiveLoginMessage, '_notExpectedType', 'prop.phoneNumber'
            ),
        }
    if not ('phoneCodeHash' in prop and type(prop['phoneCodeHash']) == str):
        return {
            'code': -1,
            'messageType': '_notExpectedType',
            'message': _getMessage.logNotRecord(
                _interactiveLoginMessage, '_notExpectedType', 'prop.phoneCodeHash'
            ),
        }

    errInfo, runIdCode, info = _checkSession(
        pageId, 'sendCode', prop['phoneNumber'], prop['phoneCodeHash']
    )
    if errInfo != None:
        return errInfo

    if info['isQrLogin']:
        nowDt = datetime.datetime.utcnow().replace(
            tzinfo=datetime.timezone.utc
        )
        return {
            'code': 5,
            'messageType': 'qrTrying',
            'message': _getMessage.log(
                runIdCode, _interactiveLoginMessage, 'qrTrying',
                int(info['qrExpiresDt'].timestamp() - nowDt.timestamp()) \
                    if info['qrExpiresDt'] != None else '---'
            ),
        }

    phoneNumber = info['phoneNumber']
    client = info['client']

    errInfo, sendCodeInfo = await _sendCode(runIdCode, client, phoneNumber)
    if errInfo != None:
        return errInfo
    else:
        info['phoneCodeHash'] = sendCodeInfo['phoneCodeHash']
        return sendCodeInfo

async def verifiedCode(pageId: str, wsId: str, prop: typing.Any = None) -> dict:
    if type(prop) != dict:
        return {
            'code': -1,
            'messageType': '_restrictedType',
            'message': _getMessage.logNotRecord(
                _interactiveLoginMessage, '_restrictedType', 'prop', 'Object'
            )
        }
    if not ('phoneNumber' in prop and type(prop['phoneNumber']) == str):
        return {
            'code': -1,
            'messageType': '_notExpectedType',
            'message': _getMessage.logNotRecord(
                _interactiveLoginMessage, '_notExpectedType', 'prop.phoneNumber'
            )
        }
    if not ('phoneCodeHash' in prop and type(prop['phoneCodeHash']) == str):
        return {
            'code': -1,
            'messageType': '_notExpectedType',
            'message': _getMessage.logNotRecord(
                _interactiveLoginMessage, '_notExpectedType', 'prop.phoneCodeHash'
            )
        }
    if not ('verifiedCode' in prop and type(prop['verifiedCode']) == str):
        return {
            'code': -1,
            'messageType': '_notExpectedType',
            'message': _getMessage.logNotRecord(
                _interactiveLoginMessage, '_notExpectedType', 'prop.verifiedCode'
            )
        }

    errInfo, runIdCode, info = _checkSession(
        pageId, 'verifiedCode', prop['phoneNumber'], prop['phoneCodeHash']
    )
    if errInfo != None:
        return errInfo

    if info['isQrLogin']:
        nowDt = datetime.datetime.utcnow().replace(
            tzinfo=datetime.timezone.utc
        )
        return {
            'code': 5,
            'messageType': 'qrTrying',
            'message': _getMessage.log(
                runIdCode, _interactiveLoginMessage, 'qrTrying',
                int(info['qrExpiresDt'].timestamp() - nowDt.timestamp()) \
                    if info['qrExpiresDt'] != None else '---'
            ),
        }

    verifiedCode = prop['verifiedCode']

    phoneNumber = info['phoneNumber']
    phoneCodeHash = info['phoneCodeHash']
    client = info['client']

    novice.logNeedle.push(
        '(runId: {}) client.sign_in() +{} with {} verifiedCode'.format(
            runIdCode, phoneNumber, verifiedCode
        )
    )
    try:
        await client.sign_in(
            code = verifiedCode,
            phone_code_hash = phoneCodeHash
        )
    except telethon.errors.SessionPasswordNeededError as err:
        try:
            passwordInfo = await client(telethon.functions.account.GetPasswordRequest())
        except Exception as err:
            errTypeName = err.__class__.__name__
            return {
                'code': -3,
                'messageType': errTypeName,
                'message': _getMessage.catchError(
                    runIdCode,
                    'client(account.GetPasswordRequest())',
                    {},
                    errTypeName
                ),
            }

        info['passwordHint'] = passwordInfo.hint
        return {
            'code': 1,
            'messageType': 'passwordNeeded',
            'message': _getMessage.log(
                runIdCode, _interactiveLoginMessage, 'passwordNeeded', passwordInfo.hint
            ),
            'hint': passwordInfo.hint,
        }
    except telethon.errors.PhoneNumberUnoccupiedError as err:
        info['verifiedCode'] = verifiedCode
        return {
            'code': 1,
            'messageType': 'phoneNumberUnoccupied',
            'message': _getMessage.log(
                runIdCode, _interactiveLoginMessage, 'phoneNumberUnoccupied'
            ),
        }
    except Exception as err:
        errTypeName = err.__class__.__name__
        return {
            'code': -3,
            'messageType': errTypeName,
            'message': _getMessage.catchError(
                runIdCode,
                'client.sign_in()',
                _signInKnownErrorTypeInfo,
                errTypeName
            ),
            'verifiedCode': verifiedCode,
        }

    _mvSessionPath(runIdCode, info['phoneNumber'], fromAddPrifix = 'tmpLogin')
    await _disconnectClient(runIdCode, info, client)

    await niUsersStatusUpdateStatus(allCount = 1, usableCount = 1)
    return {
        'code': 4,
        'messageType': 'successLogin',
        'message': _getMessage.log(
            runIdCode, _interactiveLoginMessage, 'successLogin', phoneNumber
        ),
        'phoneNumber': phoneNumber,
    }

async def verifiedPassword(pageId: str, wsId: str, prop: typing.Any = None) -> dict:
    if type(prop) != dict:
        return {
            'code': -1,
            'messageType': '_restrictedType',
            'message': _getMessage.logNotRecord(
                _interactiveLoginMessage, '_restrictedType', 'prop', 'Object'
            )
        }
    if not ('phoneNumber' in prop and type(prop['phoneNumber']) == str):
        return {
            'code': -1,
            'messageType': '_notExpectedType',
            'message': _getMessage.logNotRecord(
                _interactiveLoginMessage, '_notExpectedType', 'prop.phoneNumber'
            )
        }
    if not ('phoneCodeHash' in prop and type(prop['phoneCodeHash']) == str):
        return {
            'code': -1,
            'messageType': '_notExpectedType',
            'message': _getMessage.logNotRecord(
                _interactiveLoginMessage, '_notExpectedType', 'prop.phoneCodeHash'
            )
        }
    if not ('password' in prop and type(prop['password']) == str):
        return {
            'code': -1,
            'messageType': '_notExpectedType',
            'message': _getMessage.logNotRecord(
                _interactiveLoginMessage, '_notExpectedType', 'prop.password'
            )
        }

    errInfo, runIdCode, info = _checkSession(
        pageId, 'verifiedPassword', prop['phoneNumber'], prop['phoneCodeHash']
    )
    if errInfo != None:
        return errInfo

    if info['isQrLogin']:
        nowDt = datetime.datetime.utcnow().replace(
            tzinfo=datetime.timezone.utc
        )
        return {
            'code': 5,
            'messageType': 'qrTrying',
            'message': _getMessage.log(
                runId, _interactiveLoginMessage, 'qrTrying',
                int(info['qrExpiresDt'].timestamp() - nowDt.timestamp()) \
                    if info['qrExpiresDt'] != None else '---'
            ),
        }

    password = prop['password']

    phoneNumber = info['phoneNumber']
    phoneCodeHash = info['phoneCodeHash']
    client = info['client']

    novice.logNeedle.push(
        '(runId: {}) client.sign_in() +{} with {} password'.format(
            runIdCode, phoneNumber, password
        )
    )
    try:
        await client.sign_in(
            password = password,
            phone_code_hash = phoneCodeHash
        )
    except Exception as err:
        errTypeName = err.__class__.__name__
        return {
            'code': -3,
            'messageType': errTypeName,
            'message': _getMessage.catchError(
                runIdCode,
                'client.sign_in()/client(account.GetPasswordSettingsRequest())',
                _getPasswordSettingsKnownErrorTypeInfo,
                errTypeName
            ),
            'password': password,
            'hint': info['passwordHint'],
        }

    _mvSessionPath(runIdCode, info['phoneNumber'], fromAddPrifix = 'tmpLogin')
    await _disconnectClient(runIdCode, info, client)

    await niUsersStatusUpdateStatus(allCount = 1, usableCount = 1)
    return {
        'code': 4,
        'messageType': 'successLogin',
        'message': _getMessage.log(
            runIdCode, _interactiveLoginMessage, 'successLogin', phoneNumber
        ),
        'phoneNumber': phoneNumber,
    }

async def deleteAccount(pageId: str, wsId: str, prop: typing.Any = None) -> dict:
    if type(prop) != dict:
        return {
            'code': -1,
            'messageType': '_restrictedType',
            'message': _getMessage.logNotRecord(
                _interactiveLoginMessage, '_restrictedType', 'prop', 'Object'
            )
        }
    if not ('phoneNumber' in prop and type(prop['phoneNumber']) == str):
        return {
            'code': -1,
            'messageType': '_notExpectedType',
            'message': _getMessage.logNotRecord(
                _interactiveLoginMessage, '_notExpectedType', 'prop.phoneNumber'
            )
        }
    if not ('phoneCodeHash' in prop and type(prop['phoneCodeHash']) == str):
        return {
            'code': -1,
            'messageType': '_notExpectedType',
            'message': _getMessage.logNotRecord(
                _interactiveLoginMessage, '_notExpectedType', 'prop.phoneCodeHash'
            )
        }

    errInfo, runIdCode, info = _checkSession(
        pageId, 'deleteAccount', prop['phoneNumber'], prop['phoneCodeHash']
    )
    if errInfo != None:
        return errInfo

    if info['isQrLogin']:
        nowDt = datetime.datetime.utcnow().replace(
            tzinfo=datetime.timezone.utc
        )
        return {
            'code': 5,
            'messageType': 'qrTrying',
            'message': _getMessage.log(
                runIdCode, _interactiveLoginMessage, 'qrTrying',
                int(info['qrExpiresDt'].timestamp() - nowDt.timestamp()) \
                    if info['qrExpiresDt'] != None else '---'
            ),
        }

    phoneNumber = info['phoneNumber']
    phoneCodeHash = info['phoneCodeHash']
    client = info['client']

    novice.logNeedle.push(
        '(runId: {}) client(auth.DeleteAccountRequest()) +{}'.format(
            runIdCode, phoneNumber
        )
    )
    try:
        await client(telethon.functions.account.DeleteAccountRequest(
            reason = 'forget password'
        ))
    except telethon.errors.FloodError as err:
        # FloodError('RPCError 420: 2FA_CONFIRM_WAIT_604800 (caused by DeleteAccountRequest)')
        matchWaitTimeSec = re.search(r'^2FA_CONFIRM_WAIT_(\d+)$', err.message)
        waitTimeSec = None
        if matchWaitTimeSec != None:
            typeName = 'activeAndProtectedAccountWateConfirm'
            waitTimeSec = int(int(matchWaitTimeSec.group(1)) / 86400 * 10) / 10
        else:
            typeName = 'activeAndProtectedAccount'

        return {
            'code': 2,
            'messageType': typeName,
            'message': _getMessage.log(
                runIdCode,
                _interactiveLoginMessage,
                *(typeName, waitTimeSec) \
                    if waitTimeSec != None else typeName
            ),
            'waitTimeSec': waitTimeSec,
        }
    except Exception as err:
        errTypeName = err.__class__.__name__
        return {
            'code': -3,
            'messageType': errTypeName,
            'message': _getMessage.catchError(
                runIdCode,
                'client(auth.DeleteAccountRequest())',
                {},
                errTypeName
            ),
        }

    return {
        'code': 2,
        'messageType': 'registerAgain',
        'message': _getMessage.log(
            runIdCode, _interactiveLoginMessage, 'registerAgain', phoneNumber
        ),
    }

async def signup(pageId: str, wsId: str, prop: typing.Any = None) -> dict:
    if type(prop) != dict:
        return {
            'code': -1,
            'messageType': '_restrictedType',
            'message': _getMessage.logNotRecord(
                _interactiveLoginMessage, '_restrictedType', 'prop', 'Object'
            )
        }
    if not ('phoneNumber' in prop and type(prop['phoneNumber']) == str):
        return {
            'code': -1,
            'messageType': '_notExpectedType',
            'message': _getMessage.logNotRecord(
                _interactiveLoginMessage, '_notExpectedType', 'prop.phoneNumber'
            )
        }
    if not ('phoneCodeHash' in prop and type(prop['phoneCodeHash']) == str):
        return {
            'code': -1,
            'messageType': '_notExpectedType',
            'message': _getMessage.logNotRecord(
                _interactiveLoginMessage, '_notExpectedType', 'prop.phoneCodeHash'
            )
        }
    if not ('name' in prop and type(prop['name']) == str):
        return {
            'code': -1,
            'messageType': '_notExpectedType',
            'message': _getMessage.logNotRecord(
                _interactiveLoginMessage, '_notExpectedType', 'prop.name'
            )
        }

    errInfo, runIdCode, info = _checkSession(
        pageId, 'signup', prop['phoneNumber'], prop['phoneCodeHash']
    )
    if errInfo != None:
        return errInfo

    firstName = prop['name']

    phoneNumber = info['phoneNumber']
    phoneCodeHash = info['phoneCodeHash']
    client = info['client']

    novice.logNeedle.push(
        '(runId: {}) client.sign_up() +{}'.format(runIdCode, phoneNumber)
    )
    try:
        await client.sign_up(
            info['verifiedCode'],
            firstName,
            '',
            phone_code_hash = phoneCodeHash
        )
    except Exception as err:
        errTypeName = err.__class__.__name__
        return {
            'code': -3,
            'messageType': errTypeName,
            'message': _getMessage.catchError(
                runIdCode,
                'client.sign_up()',
                _signUpKnownErrorTypeInfo,
                errTypeName
            ),
        }

    _mvSessionPath(runIdCode, info['phoneNumber'], fromAddPrifix = 'tmpLogin')
    await _disconnectClient(runIdCode, info, client)

    await niUsersStatusUpdateStatus(allCount = 1, usableCount = 1)
    return {
        'code': 4,
        'messageType': 'successSingup',
        'message': _getMessage.log(
            runIdCode, _interactiveLoginMessage, 'successSingup', phoneNumber
        ),
        'phoneNumber': phoneNumber,
    }


_interactiveLoginMessage = {
    '_undefined': 'Unexpected log message.',
    '_undefinedError': 'Unexpected error message.',
    '_illegalInvocation': 'Illegal invocation.',
    '_notExpectedType': '"{}" is not of the expected type.',
    '_restrictedType': '"{}" must be a `{}` type.',
    # -3 登入錯誤
    # -2 互動錯誤
    'noUserToLogin': '沒有待登入的用戶。',
    'userNotSame': '登入的仿用戶 (+{}) 與主機留存仿用戶 (+{}) 不相同',
    'qrUnknownType': 'QR 碼驗證方法失敗 (type: {})',
    'qrErrorOnCheck': '無法取得 QR 碼驗證結果，請再嘗試一次。 (type: {})',
    # -1 程式錯誤
    # 1 驗證碼互動
    'sendCode': '已使用 {} 傳送驗證碼。',
    'sendCodeAndNext': '已使用 {} 傳送驗證碼。 (下次將使用 {} 傳送驗證碼)',
    'sendCodeAndNextHasTimeout':
        '已使用 {} 傳送驗證碼。 (再 {} 秒後將使用 {} 傳送驗證碼)',
    'passwordNeeded': '啟用了兩步驗證，需要輸入密碼。 (提示： {})',
    'phoneNumberUnoccupied': '註冊新帳戶。',
    # 2 密碼互動
    'activeAndProtectedAccount':
        '活躍帳戶出於安全考慮，我們將在一週內將其刪除。',
    'activeAndProtectedAccountWateConfirm':
        '活躍帳戶出於安全考慮，您可以在 {} 天後重設帳戶。',
    'registerAgain': '重新註冊帳戶',
    # 3 註冊互動
    # 4 登入/註冊成功
    'loggedin': '+{} 仿用戶已登入',
    'successLogin': '+{} 仿用戶登入成功',
    'successSingup': '+{} 仿用戶註冊成功',
    # 5 其他互動 (二維碼)
    'qrRequestReceived': '請稍待 QR 碼',
    'qrToken': '請掃描 QR 碼驗證 (於 {} 秒後過期)',
    'qrTrying': '目前正使用 QR 碼驗證中 (於 {} 秒後過期)',
    'qrTokenExpired': 'QR 碼已過期，請再嘗試一次。',
}
_sendCodeKnownErrorTypeInfo = {
    'ApiIdInvalidError': 'API ID 無效。',
    'ApiIdPublishedFloodError': '該 API ID 已發佈在某個地方，您現在無法使用。',
    'InputRequestTooLongError': '輸入的請求太長。 (*這可能是程式庫的錯誤)',
    'PhoneNumberAppSignupForbiddenError': '您無法使用此應用程式註冊',
    'PhoneNumberBannedError': '提供的電話號碼已被電報禁止，無法再使用。也許可查閱 https://www.telegram.org/faq_spam。',
    'PhoneNumberFloodError': '您請求代碼的次數過多。',
    'PhoneNumberInvalidError': '電話號碼是無效的。',
    'PhonePasswordFloodError': '您嘗試登錄太多次了。',
    'PhonePasswordProtectedError': '此電話受密碼保護。',
    # 沒有在 https://core.telegram.org/method/auth.sendCode 的錯誤
    'AuthRestartError': '重新啟動授權過程。',
    # 沒有在 https://tl.telethon.dev/methods/auth/send_code.html 的錯誤
    # 401 AUTH_KEY_PERM_EMPTY
    # 303 NETWORK_MIGRATE_X
    # 303 PHONE_MIGRATE_X
}
_signInKnownErrorTypeInfo = {
    'PhoneCodeEmptyError': '驗證碼丟失。',
    'PhoneCodeExpiredError': '驗證碼已過期。',
    'PhoneCodeInvalidError': '驗證碼錯誤。',
    'PhoneNumberInvalidError': '電話號碼是無效的。',
    # 'PhoneNumberUnoccupiedError': '電話號碼尚未使用。',
    # 沒有在 https://core.telegram.org/method/auth.sendCode 的錯誤
    # 'SessionPasswordNeededError': '啟用了兩步驗證，並且需要密碼。',
}
_getPasswordSettingsKnownErrorTypeInfo = {
    'PasswordHashInvalidError': '密碼錯誤。'
}
_signUpKnownErrorTypeInfo = {
    'FirstNameInvalidError': '名字無效。',
    'PhoneCodeEmptyError': '驗證碼丟失。 (*程式錯誤)',
    'PhoneCodeExpiredError': '驗證碼已過期。',
    'PhoneCodeInvalidError': '驗證碼錯誤。',
    'PhoneNumberFloodError': '您請求代碼的次數過多。',
    'PhoneNumberInvalidError': '電話號碼是無效的。',
    'PhoneNumberOccupiedError': '該電話號碼已被使用。',
    # 只在 https://core.telegram.org/method/auth.signUp 的錯誤
    # 400 LASTNAME_INVALID
    # 只在 https://tl.telethon.dev/methods/auth/sign_up.html 的錯誤
    'MemberOccupyPrimaryLocFailedError': 'Occupation of primary member location failed.',
}

class _getMessage():
    def logNotRecord(msgTypeInfos: dict, typeName: str, *args) -> str:
        if typeName in msgTypeInfos:
            msg = msgTypeInfos[typeName]
            if len(args) > 0:
                msg = msg.format(*args)
        else:
            msg = '{} (type: {})'.format(
                _interactiveLoginMessage['_undefined'],
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
                _interactiveLoginMessage['_undefined'],
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
                _interactiveLoginMessage['_undefinedError'],
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

def _checkSession(
        pageId: str,
        methodName: str,
        arguPhoneNumber: str,
        arguPhoneCodeHash: str) -> typing.Tuple[typing.Union[None, dict], str, dict]:
    innerSession = serverMix.innerSession.get(pageId)

    isHasSession = 'interactiveLogin' in innerSession
    if isHasSession:
        info = innerSession['interactiveLogin']
        runId = info['runId']
    else:
        runId = random.randrange(1000000, 9999999)
        info = innerSession['interactiveLogin'] = {
            'runId': runId,
            'phoneNumber': '',
            'phoneCodeHash': '',
            'isQrLogin': False,
            'qrExpiresDt': None,
            'verifiedCode': '',
            'passwordHint': '',
            'client': None,
        }

    phoneNumber = arguPhoneNumber \
        if methodName == 'login' or not isHasSession \
        else info['phoneNumber']
    runIdCode = '{}-{}'.format(runId, phoneNumber)
    novice.logNeedle.push(
        '(runId: {}) {} +{}'.format(runIdCode, methodName, phoneNumber)
    )

    errInfo = None
    if methodName != 'login':
        if info['client'] == None:
            errInfo = {
                'code': -2,
                'messageType': 'noUserToLogin',
                'message': _getMessage.log(
                    runIdCode, _interactiveLoginMessage, 'noUserToLogin'
                ),
            }

        currPhoneNumber = info['phoneNumber']
        if currPhoneNumber != arguPhoneNumber \
                or info['phoneCodeHash'] != arguPhoneCodeHash:
            errInfo = {
                'code': -2,
                'messageType': 'userNotSame',
                'message': _getMessage.log(
                    runIdCode,
                    _interactiveLoginMessage,
                    'userNotSame', arguPhoneNumber, currPhoneNumber
                ),
                'phoneNumber': currPhoneNumber,
                'anotherPhoneNumber': arguPhoneNumber,
            }

    return (errInfo, runIdCode, info)

async def _checkConnectClient(
        runIdCode: str,
        tgSessionAddPrifix: str,
        phoneNumber: str
        ) -> typing.Tuple[typing.Union[None, dict], typing.Union[None, TelegramClient]]:
    client = TelegramClient(
        tgSession.getSessionPath(
            phoneNumber,
            addPrifix = tgSessionAddPrifix,
            noExt = True
        ),
        novice.py_env['apiId'],
        novice.py_env['apiHash']
    )

    try:
        novice.logNeedle.push('(runId: {}) client.connect()'.format(runIdCode))
        await client.connect()
    except Exception as err:
        errTypeName = err.__class__.__name__
        errMsg = _getMessage.catchError(runIdCode, 'client.connect()', {}, errTypeName)
        _mvSessionPath(
            runIdCode,
            phoneNumber,
            fromAddPrifix = tgSessionAddPrifix,
            toAddPrifix = 'undefinedError'
        )
        return (
            {'code': -3, 'messageType': errTypeName, 'message': errMsg},
            None
        )

    return (None, client)

async def _disconnectClient(runIdCode: str, info: dict, client: TelegramClient) -> None:
    novice.logNeedle.push('(runId: {}) disconnect'.format(runIdCode))
    await client.disconnect()
    info['phoneNumber'] = ''
    info['phoneCodeHash'] = ''
    info['client'] = None

async def _sendCode(
        runIdCode: str,
        client: TelegramClient,
        phoneNumber: str
        ) -> typing.Tuple[typing.Union[None, dict], typing.Union[None, dict]]:
    # 如果已登入的狀態不該存在 "tmpLogin" 前綴的路徑下
    # 所以無需測試 `client.is_user_authorized()` 方法
    novice.logNeedle.push('(runId: {}) client.send_code_request()'.format(runIdCode))
    try:
        sentCode = await client.send_code_request(phoneNumber)
    except Exception as err:
        errTypeName = err.__class__.__name__
        errMsg = _getMessage.catchError(
            runIdCode,
            'client.send_code_request()',
            _sendCodeKnownErrorTypeInfo,
            errTypeName
        )
        return ({'code': -3, 'messageType': errTypeName, 'message': errMsg}, None)

    currCodeType = type(sentCode.type)
    nextCodeType = type(sentCode.next_type) \
        if sentCode.next_type != None else None

    if currCodeType == telethon.types.auth.SentCodeTypeApp:
        currMode = 'App'
    elif currCodeType == telethon.types.auth.SentCodeTypeSms:
        currMode = 'SMS'
    elif currCodeType == telethon.types.auth.SentCodeTypeCall:
        currMode = 'Call'
    else:
        currMode = 'type({})'.format(currCodeType.__name__)

    if nextCodeType == None:
        nextMode = 'nothing'
    elif nextCodeType == telethon.types.auth.CodeTypeSms:
        nextMode = 'SMS'
    elif nextCodeType == telethon.types.auth.CodeTypeCall:
        nextMode = 'Call'
    else:
        nextMode = 'type({})'.format(nextCodeType.__name__)

    nextSendTimeSec = sentCode.timeout

    if nextCodeType == None:
        typeName = 'sendCode'
        sendMsg = _getMessage.logNotRecord(
            _interactiveLoginMessage, 'sendCode', currMode
        )
    elif nextSendTimeSec == None:
        typeName = 'sendCodeAndNext'
        sendMsg = _getMessage.logNotRecord(
            _interactiveLoginMessage, 'sendCodeAndNext', currMode, nextMode
        )
    else:
        typeName = 'sendCodeAndNextHasTimeout'
        sendMsg = _getMessage.logNotRecord(
            _interactiveLoginMessage,
            'sendCodeAndNextHasTimeout', currMode, nextSendTimeSec, nextMode
        )

    phoneCodeHash = sentCode.phone_code_hash
    novice.logNeedle.push(
        '(runId: {}) {} (phoneCodeHash: {})'.format(
            runIdCode, sendMsg, phoneCodeHash
        )
    )
    return (None, {
        'code': 1,
        'messageType': typeName,
        'message': sendMsg,
        'phoneNumber': phoneNumber,
        'phoneCodeHash': phoneCodeHash,
    })

def _mvSessionPath(
        runIdCode: str,
        phoneNumber: str,
        fromAddPrifix: str = '',
        toAddPrifix: str = '') -> None:
    novice.logNeedle.push(
        '(runId: {}) move +{} session from {} to {}'.format(
            runIdCode,
            phoneNumber,
            fromAddPrifix if fromAddPrifix != '' else '_',
            toAddPrifix if toAddPrifix != '' else '_'
        )
    )
    tgSession.mvSessionPath(
        phoneNumber,
        fromAddPrifix = fromAddPrifix,
        toAddPrifix = toAddPrifix
    )

