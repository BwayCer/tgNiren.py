#!/usr/bin/env python3


import pdb
import typing
import os
import getpass
import datetime
import re
import random
import asyncio
import base64
import telethon.sync as telethon
import tgkream.errors as errors
import utils.novice as novice
from tgkream.utils import TgTypeing, TgSession, TgDefaultInit


__all__ = [
    'errors', 'knownError',
    'telethon', 'TgTypeing', 'TgDefaultInit', 'TgSimple'
]


TelegramClient = telethon.TelegramClient

knownError = errors.knownError


class TgSimple(TgSession):
    def __init__(self,
            apiId: int,
            apiHash: str,
            sessionPrifix: str,
            papaPhone: str = 0):
        TgSession.__init__(self, sessionPrifix)

        self._apiId = apiId
        self._apiHash = apiHash

    # if phoneNumber == '+8869xxx', input '8869xxx' (str)
    async def login(self, phoneNumber: str) -> typing.Union[None, TelegramClient]:
        print('-> login +{}'.format(phoneNumber))
        sessionPath = self.getSessionPath(phoneNumber)

        if not os.path.exists(sessionPath):
            print(errors.errMsg.SessionFileNotExistsTemplate.format(phoneNumber))

        client = TelegramClient(
            self.getSessionPath(phoneNumber, noExt = True),
            self._apiId,
            self._apiHash
        )
        isLoginSuccess = await _interactiveLogin(phoneNumber, client, self._apiId, self._apiHash)

        print('--- login +{} {} ---'.format(
            phoneNumber,
            'success' if isLoginSuccess else 'failed'
        ))
        return client if isLoginSuccess else None

    async def loginPick(self, phoneNumbersTxt: str) -> list:
        print('--- loginPick start ---')
        phoneNumbers = phoneNumbersTxt.split(',')
        clientInfoList = []

        for idx in range(len(phoneNumbers)):
            phoneNumber = phoneNumbers[idx]

            clientInfo = None
            if phoneNumber != '':
                client = await self.login(phoneNumber)
                myInfo = await client.get_me()
                self._clientInfoList.append({
                    'id': myInfo.phone,
                    'userId': myInfo.id,
                    'client': client,
                })
            clientInfoList[idx] = clientInfo

        print('--- loginPick end ---')
        return clientInfoList

    def getRandId(self):
        return random.randrange(1000000, 9999999)

    async def iterLoopInterval(self, length: int, circleInterval: float = 1) -> None:
        prevTimeMs = novice.dateUtcNowTimestamp()
        idxLoop = 0
        while True:
            if circleInterval > 0 and idxLoop != 0:
                nowTimeMs = novice.dateUtcNowTimestamp()
                intervalTimeMs = circleInterval - ((nowTimeMs - prevTimeMs) / 1000)
                if intervalTimeMs > 0:
                    print('wait {} second'.format(intervalTimeMs))
                    await asyncio.sleep(intervalTimeMs)
                    prevTimeMs = novice.dateUtcNowTimestamp()
                else:
                    prevTimeMs = nowTimeMs

            yield idxLoop
            idxLoop += 1
            if 0 < length and length <= idxLoop:
                break


async def _interactiveLogin(phoneNumber: str, client: TelegramClient, apiId: int, apiHash: str) -> bool:
    print('--> client.connect()')
    try:
        await client.connect()
    except Exception as err:
        print('{} Error: {} (from: {})'.format(type(err), err, 'client.connect()'))
        raise err

    print('--> client.is_user_authorized()')
    if await client.is_user_authorized():
        return True

    print(errors.errMsg.UserNotAuthorizedTemplate.format(phoneNumber))

    # https://core.telegram.org/api/auth
    # https://docs.telethon.dev/en/latest/modules/client.html
    # https://docs.telethon.dev/en/latest/modules/client.html#telethon.client.auth.AuthMethods.send_code_request
    signInMethod = 'sendCode'
    phoneCodeHash = ''
    isCanChangeSendCodeMode = True
    nextSendMode = 'nothing'
    prevPasswordInfoSrpId = 0
    passwordInfo = None
    isNotSendPasswordRecoveryCode = True
    try:
        while True:
            if signInMethod == 'finish':
                return True
            elif signInMethod == 'failed':
                return False
            elif signInMethod == 'sendCode':
                print('---> client.send_code_request()')

                # https://tl.telethon.dev/methods/auth/send_code.html
                # 第一次
                #   SentCode(
                #     type=SentCodeTypeApp(length=5),
                #     phone_code_hash='9422f386fdbcd423af',
                #     next_type=CodeTypeSms(),
                #     timeout=None
                #   )
                # 第二次
                #   SentCode(
                #     type=SentCodeTypeSms(length=5),
                #     phone_code_hash='9422f386fdbcd423af',
                #     next_type=CodeTypeCall(),
                #     timeout=120
                #   )
                # 第三次
                #   SentCode(
                #     type=SentCodeTypeCall(length=5),
                #     phone_code_hash='9422f386fdbcd423af',
                #     next_type=None,
                #     timeout=None
                #   )
                # 第四次
                #   SentCode(
                #     type=SentCodeTypeSms(length=5),
                #     phone_code_hash='9422f386fdbcd423af',
                #     next_type=None(),
                #     timeout=None
                #   )
                try:
                    # NOTE:
                    # 可以強制發送 SMS 訊息，
                    # 也可以請求兩次自動使用下一個方式傳送訊息 (沒有間隔時間限制)
                    #   await client.send_code_request(phoneNumber, force_sms = True)
                    #   or
                    #   await client.send_code_request(phoneNumber)
                    sentCode = await client.send_code_request(phoneNumber)
                    # or
                    # sentCode = await client.sign_in(phoneNumber)
                except Exception as err:
                    signInMethod = 'failed'
                    errType = type(err)
                    if telethon.errors.ApiIdInvalidError == errType:
                        print('API ID 無效。')
                    elif telethon.errors.PhoneNumberBannedError == errType:
                        print('The phone {} is Banned.'.format(phoneNumber))
                    elif telethon.errors.PhoneNumberFloodError == errType:
                        print('您請求代碼的次數過多。')
                    elif telethon.errors.PhoneNumberInvalidError == errType:
                        print('電話號碼是無效的。')
                    elif telethon.errors.PhonePasswordFloodError == errType:
                        print('您嘗試登錄太多次了。')
                    else:
                        print('{} Error: {} (from: {})'.format(
                            errType, err, 'client.send_code_request()'
                        ))
                        raise err

                    continue

                phoneCodeHash = sentCode.phone_code_hash
                isCanChangeSendCodeMode = sentCode.next_type != None
                currCodeType = type(sentCode.type)
                nextCodeType = type(sentCode.next_type) \
                    if isCanChangeSendCodeMode else None
                nextSendTimeSec = sentCode.timeout
                if currCodeType == telethon.types.auth.SentCodeTypeApp:
                    currMode = 'App'
                elif currCodeType == telethon.types.auth.SentCodeTypeSms:
                    currMode = 'SMS'
                elif currCodeType == telethon.types.auth.SentCodeTypeCall:
                    currMode = 'Call'
                else:
                    currMode = 'type({})'.format(type(currCodeType))

                if nextCodeType == None:
                    nextSendMode = 'nothing'
                elif nextCodeType == telethon.types.auth.CodeTypeSms:
                    nextSendMode = 'SMS'
                elif nextCodeType == telethon.types.auth.CodeTypeCall:
                    nextSendMode = 'Call'
                else:
                    nextSendMode = 'type({})'.format(type(nextCodeType))

                sendCodeMsg = '----> 已使用 {} 傳送驗證碼'.format(currMode)
                if isCanChangeSendCodeMode:
                    if nextSendTimeSec == None:
                        sendCodeMsg += ' (下次將使用 {} 傳送驗證碼)'.format(nextSendMode)
                    else:
                        sendCodeMsg += ' (再 {} 秒後將使用 {} 傳送驗證碼)'.format(nextSendTimeSec, nextSendMode)

                    sendCodeMsg += ' (phoneCodeHash: {})'.format(phoneCodeHash)
                print(sendCodeMsg)

                signInMethod = 'qrLogin'
            elif signInMethod == 'qrLogin':
                useQrcodeModeInput = _inputYesOrNo(input(
                    f'login {phoneNumber}, Whether to login by QR code ? [Y/N]: '
                ))
                if useQrcodeModeInput == 'yes':
                    pass
                elif useQrcodeModeInput == 'no':
                    signInMethod = 'changeSendCodeMode'
                    continue
                else:
                    continue

                isLoginSuccess = False
                while True:
                    print('----> client(auth.ExportLoginTokenRequest)')
                    try:
                        exportLoginTokenResult = await client(telethon.functions.auth.ExportLoginTokenRequest(
                            api_id = apiId,
                            api_hash = apiHash,
                            except_ids = []
                        ))
                    except Exception as err:
                        print('{} Error: {} (from: {})'.format(
                            type(err), err, 'client(auth.ExportLoginTokenRequest)'
                        ))
                        raise err

                    if type(exportLoginTokenResult) \
                            == telethon.types.auth.LoginTokenSuccess:
                        print('-----> 其實已登入')
                        isLoginSuccess = True
                        break

                    print('-----> QR Token: tg://login?token={}'.format(
                        base64.b64encode(exportLoginTokenResult.token).decode()
                    ))
                    while True:
                        # 無法使用 `await client.is_user_authorized()` 檢查是否已登入

                        nowDt = datetime.datetime.utcnow().replace(
                            tzinfo=datetime.timezone.utc
                        )
                        if nowDt >= exportLoginTokenResult.expires:
                            break
                        await asyncio.sleep(3)

                    if isLoginSuccess == True:
                        break

                    useQrcodeModeInput = _inputYesOrNo(input(
                        f'login {phoneNumber}, Is continue to login by QR code ? [Y/N]: '
                    ))
                    if useQrcodeModeInput == 'yes':
                        continue
                    else:
                        break

                if isLoginSuccess == True:
                    signInMethod = 'finish'
                else:
                    signInMethod = 'changeSendCodeMode'
            elif signInMethod == 'changeSendCodeMode':
                if isCanChangeSendCodeMode:
                    useNextSendCodeModeInput = _inputYesOrNo(input(
                        'login {}, Whether to notify by {} ? [Y/N]: '
                            .format(phoneNumber, nextSendMode)
                    ))
                    if useNextSendCodeModeInput == 'yes':
                        signInMethod = 'sendCode'
                    elif useNextSendCodeModeInput == 'no':
                        signInMethod = 'inputCode'
                    else:
                        continue
                else:
                    signInMethod = 'inputCode'
                    continue
            elif signInMethod == 'inputCode':
                verifiedCode = input('login {}, Enter the code: '.format(phoneNumber))
                if verifiedCode == '':
                    print('----> 請提供驗證碼。')
                    continue

                # https://tl.telethon.dev/methods/auth/sign_in.html
                print('----> client.sign_in() with {} verifiedCode'.format(verifiedCode))
                try:
                    await client.sign_in(
                        code = verifiedCode,
                        phone_code_hash = phoneCodeHash
                    )
                    # or
                    # await client.sign_in(code = verifiedCode)

                    signInMethod = 'finish'
                except telethon.errors.PhoneCodeInvalidError as err:
                    print('驗證碼錯誤。')
                    signInMethod = 'changeSendCodeMode'
                except telethon.errors.PhoneNumberUnoccupiedError as err:
                    print('電話號碼尚未使用。')
                    signInMethod = 'signup'
                except telethon.errors.SessionPasswordNeededError as err:
                    # print('已設定使用二次驗證登入方式。')
                    print('---> 設定使用二次驗證登入方式')
                    signInMethod = '2FaVerification'
                except telethon.errors.PhoneCodeEmptyError as err:
                    print('驗證碼丟失。')
                except telethon.errors.PhoneCodeExpiredError as err:
                    signInMethod = 'failed'
                    print('驗證碼已過期。')
                except telethon.errors.PhoneNumberInvalidError as err:
                    signInMethod = 'failed'
                    print('電話號碼是無效的。')
                except Exception as err:
                    print('{} Error: {} (from: {})'.format(
                        type(err), err, 'client.sign_in()'
                    ))
                    raise err
            elif signInMethod == '2FaVerification':
                # https://telethonn.readthedocs.io/en/latest/extra/basic/creating-a-client.html#two-factor-authorization-2fa

                # NOTE:
                # passwordInfo 是會被更新的 (且登入後 `passwordInfo.srp_id` 也會不一樣)
                # srp 是啥? 我也不懂 https://core.telegram.org/api/srp
                passwordInfo = await client(telethon.functions.account.GetPasswordRequest())
                if prevPasswordInfoSrpId != passwordInfo.srp_id:
                    prevPasswordInfoSrpId = passwordInfo.srp_id
                    isNotSendPasswordRecoveryCode = True
                # Password(
                #     new_algo=PasswordKdfAlgoSHA256SHA256PBKDF2HMACSHA512iter100000SHA256ModPow(
                #         salt1=b'V\x95...\x99',
                #         salt2=b'*m\xfb...\x14',
                #         g=3,
                #         p=b'\xc7...\xcc['
                #     ),
                #     new_secure_algo=SecurePasswordKdfAlgoPBKDF2HMACSHA512iter100000(
                #         salt=b'\xe0...\xac'
                #     ),
                #     secure_random=b'\x94G...\x82',
                #     has_recovery=True,
                #     has_secure_values=False,
                #     has_password=True,
                #     current_algo=PasswordKdfAlgoSHA256SHA256PBKDF2HMACSHA512iter100000SHA256ModPow(
                #         salt1=b'V\x95...\xddv(B?',
                #         salt2=b'*m\xfb...\x14',
                #         g=3,
                #         p=b'\xc7...\xcc['
                #     ),
                #     srp_B=b'D\x02...\xd7',
                #     srp_id=4395752765720487710,
                #     hint='123',
                #     email_unconfirmed_pattern=None
                # )

                password = getpass.getpass(
                    'login {}, Enter the password (hint: {}): '.format(
                        phoneNumber,
                        passwordInfo.hint
                    )
                )

                if password == '':
                    print('----> 請提供二次驗證密碼。')
                    continue

                # https://tl.telethon.dev/methods/auth/check_password.html
                print('----> client.sign_in() with password')
                try:
                    await client.sign_in(
                        password = password,
                        phone_code_hash = phoneCodeHash
                    )
                    # or
                    # await client.sign_in(password = password)

                    signInMethod = 'finish'
                except telethon.errors.PasswordHashInvalidError as err:
                    print('二次驗證密碼錯誤。')
                    signInMethod = 'forget2FaVerification'
                    continue
                except Exception as err:
                    print('{} Error: {} (from: {})'.format(
                        type(err), err, 'client.sign_in()'
                    ))
                    raise err
            elif signInMethod == 'forget2FaVerification':
                forget2FaVerificationInput = _inputYesOrNo(
                    input('login {}, forget password ? (Yes or No): '.format(phoneNumber))
                )

                if forget2FaVerificationInput == 'yes':
                    if passwordInfo.has_recovery:
                        useRecoveryPasswordInput = _inputYesOrNo(input(
                            'login {}, recovery password ? (Yes or No): '
                                .format(phoneNumber)
                        ))
                        if useRecoveryPasswordInput == 'yes':
                            print('----> 移除二次驗證碼')
                            signInMethod = 'passwordRecovery'
                            continue
                        elif useRecoveryPasswordInput == 'no':
                            pass
                        else:
                            continue

                    useDeleteAccountInput = _inputYesOrNo(input(
                        'login {}, delete account ? (Yes or No): '
                            .format(phoneNumber)
                    ))
                    if useDeleteAccountInput == 'yes':
                        print('----> 重置帳戶')
                        signInMethod = 'deleteAccount'
                        continue
                    elif useDeleteAccountInput == 'no':
                        pass
                    else:
                        continue

                    signInMethod = '2FaVerification'
                elif forget2FaVerificationInput == 'no':
                    signInMethod = '2FaVerification'
                else:
                    continue
            elif signInMethod == 'passwordRecovery':
                # 移除二次驗證碼
                # https://core.telegram.org/method/auth.requestPasswordRecovery
                # https://core.telegram.org/method/auth.recoverPassword
                # https://tl.telethon.dev/methods/auth/request_password_recovery.html
                # https://tl.telethon.dev/methods/auth/recover_password.html
                if isNotSendPasswordRecoveryCode:
                    try:
                        print('-----> client(auth.RequestPasswordRecoveryRequest)')
                        passwordRecoveryInfo = await client(
                            telethon.functions.auth.RequestPasswordRecoveryRequest()
                        )
                        print('------> 傳送恢復密碼代碼至 {} 信箱'.format(
                            passwordRecoveryInfo.email_pattern
                        ))
                    except Exception as err:
                        print('{} Error: {} (from: {})'.format(
                            type(err), err,
                            'client(auth.RequestPasswordRecoveryRequest)'
                        ))
                        raise err

                recoveryCode = input('login {}, Enter the password recovery code: '.format(phoneNumber))
                if recoveryCode == '':
                    print('-----> 請提供恢復密碼代碼。')
                    continue

                print(
                    '-----> client(auth.RecoverPasswordRequest) with {} recovery code'
                        .format(recoveryCode)
                )
                try:
                    await client(telethon.functions.auth.RecoverPasswordRequest(
                        code = recoveryCode
                    ))

                    signInMethod = 'finish'
                except telethon.errors.CodeEmptyError as err:
                    print('恢復密碼代碼丟失。')
                    continue
                except telethon.errors.CodeInvalidError as err:
                    # CodeInvalidError('Code invalid (i.e. from email) (caused by RecoverPasswordRequest)')
                    print('恢復密碼代碼錯誤。')
                    continue
                except Exception as err:
                    print('{} Error: {} (from: {})'.format(
                        type(err), err, 'client(auth.RecoverPasswordRequest)'
                    ))
                    raise err
            elif signInMethod == 'deleteAccount':
                # 刪除帳戶
                # https://core.telegram.org/method/account.deleteAccount
                # https://tl.telethon.dev/methods/account/delete_account.html
                print('-----> client(auth.DeleteAccountRequest)')
                try:
                    await client(telethon.functions.account.DeleteAccountRequest(
                        reason = 'forget password'
                    ))
                except telethon.errors.FloodError as err:
                    # FloodError('RPCError 420: 2FA_CONFIRM_WAIT_604800 (caused by DeleteAccountRequest)')
                    signInMethod = 'failed'
                    errMsg = '活躍帳戶出於安全考慮，我們將在一週內將其刪除。'
                    matchWaitTimeSec = re.search(
                        r'^2FA_CONFIRM_WAIT_(\d+)$',
                        err.message
                    )
                    if matchWaitTimeSec:
                        print('活躍帳戶出於安全考慮，您可以在 {} 天後重設帳戶。' .format(
                            int(int(matchWaitTimeSec.group(1)) / 86400 * 10) / 10
                        ))
                    else:
                        print('活躍帳戶出於安全考慮，我們將在一週內將其刪除。')
                except Exception as err:
                    print('{} Error: {} (from: {})'.format(
                        type(err), err, 'client(auth.DeleteAccountRequest)'
                    ))
                    raise err

                signInMethod = 'signup'
            elif signInMethod == 'signup':
                print('---> 註冊新帳戶')
                signInMethod = 'signup_start'
            elif signInMethod == 'signup_start':
                firstName = input('sign up {}, Enter the firstName: '.format(phoneNumber))
                lastName = input('sign up {}, Enter the lastName: '.format(phoneNumber))

                # https://core.telegram.org/method/auth.signUp
                # https://tl.telethon.dev/methods/auth/sign_up.html
                print('----> client.sign_up()')
                try:
                    await client.sign_up(
                        verifiedCode,
                        firstName,
                        lastName,
                        phone_code_hash = phoneCodeHash
                    )
                    # or
                    # await client.sign_up(verifiedCode, firstName, lastName)

                    # 成功的話會出現下列訊息 :
                    # By signing up for Telegram, you agree not to:
                    #
                    # - Use our service to send spam or scam users.
                    # - Promote violence on publicly viewable Telegram bots, groups or channels.
                    # - Post pornographic content on publicly viewable Telegram bots, groups or channels.
                    #
                    # We reserve the right to update these Terms of Service later.

                    signInMethod = 'finish'
                except telethon.errors.FirstNameInvalidError as err:
                    print('名字無效。')
                except telethon.errors.PhoneCodeInvalidError as err:
                    print('驗證碼錯誤。')
                except telethon.errors.MemberOccupyPrimaryLocFailedError as err:
                    print('Occupation of primary member location failed.')
                except telethon.errors.PhoneCodeEmptyError as err:
                    signInMethod = 'failed'
                    print('驗證碼丟失。')
                except telethon.errors.PhoneCodeExpiredError as err:
                    signInMethod = 'failed'
                    print('驗證碼已過期。')
                except telethon.errors.PhoneNumberFloodError as err:
                    signInMethod = 'failed'
                    print('您請求代碼的次數過多。')
                except telethon.errors.PhoneNumberInvalidError as err:
                    signInMethod = 'failed'
                    print('電話號碼是無效的。')
                except telethon.errors.PhoneNumberOccupiedError as err:
                    signInMethod = 'failed'
                    print('該電話號碼已被使用。')
                except telethon.errors.RegIdGenerateFailedError as err:
                    signInMethod = 'failed'
                    print('生成註冊 ID 時失敗。')
                except Exception as err:
                    print('{} Error: {} (from: {})'.format(
                        type(err), err, 'client.sign_up()'
                    ))
                    raise err
    except Exception as err:
        print('{} Error: {} '.format(type(err), err))
        pdb.set_trace()
        raise err

def _inputYesOrNo(inputTxt: str) -> str:
    if inputTxt == 'Yes' or inputTxt == 'yes' or inputTxt == 'Y' or inputTxt == 'y':
        return 'yes'
    elif inputTxt == 'No' or inputTxt == 'no' or inputTxt == 'N' or inputTxt == 'n':
        return 'no'
    else:
        return inputTxt

