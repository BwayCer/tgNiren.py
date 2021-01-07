#!/usr/bin/env python3


import typing
import os
import platform
import math
import random
import datetime
import re
import asyncio
import requests
import telethon as telethon
import utils.json
import utils.novice as novice
import webBox.serverMix as serverMix
import webBox.app.utils as appUtils
from webBox.app._wsChannel.niUsersStatus import updateStatus as niUsersStatusUpdateStatus


__all__ = ['add', 'autoSignUp']


TelegramClient = telethon.TelegramClient
_tgAppMain = novice.py_env['tgApp']['main']

_sessionDirPath = novice.py_dirname + '/' + novice.py_env['tgSessionDirPath']
_envModemPool = novice.py_env['modemPool']
_modemPoolDataFilePath = novice.py_dirname + '/' + _envModemPool['dataFilePath']
_nameListFilePath = novice.py_dirname + '/' + _envModemPool['nameListFilePath']
_photoDirPath = novice.py_dirname + '/' + _envModemPool['photoPath']

_scanTaskMultiple = 3 # 使用需求數的 X 倍數同時掃描
_scanTaskMax = 20 # 單次同時掃描的最大值
_config_confirmTimeoutSec = 0.1
_config_inputTimeoutSec = 0.1
_config_requestSmsTimeoutSec = 0.1


def add(pageId: str, wsId: str, prop: typing.Any = None) -> dict:
    if type(prop) != dict:
        return {
            'code': -1,
            'message': appUtils.console.getErrorMsg(
                appUtils.console.baseMsg, '_notExpectedType', 'prop', 'Object'
            ),
        }
    if not ('modemCardsTxt' in prop and type(prop['modemCardsTxt']) == str):
        return {
            'code': -1,
            'message': appUtils.console.getErrorMsg(
                appUtils.console.baseMsg, '_notExpectedType', 'prop.modemCardsTxt'
            ),
        }

    smsUrlFormat = _envModemPool['smsUrlFormat']

    modemCardsTxt = prop['modemCardsTxt']

    runIdCode = str(random.randrange(1000000, 9999999))
    modemPoolTable = ModemPoolTable(_modemPoolDataFilePath)
    regeCindyVoipTxt = r'^(\d+)\|([0-9a-fA-F]+)$'

    totalCount = 0
    addCount = 0
    for line in modemCardsTxt.splitlines():
        totalCount += 1
        matchTgCode = re.search(regeCindyVoipTxt, line)

        if not matchTgCode:
            return {
                'code': -1,
                'message': appUtils.console.getErrorMsg(
                    _cindyAddMessage, 'notExpectedModemCardLineFormat', line
                ),
            }

        phone = matchTgCode.group(1)
        token = matchTgCode.group(2)

        modemCardInfo = modemPoolTable.whichPhone('1' + phone)
        if modemCardInfo != None and token == modemCardInfo['token']:
            continue

        addCount += 1
        modemPoolTable.addModemCard('1' + phone, token, smsUrlFormat)

    modemPoolTable.gatherModemCardInfo()
    modemPoolTable.store()

    return {
        'code': 1,
        'message': appUtils.console.log(
            runIdCode, _cindyAddMessage,
            'successAddModemCards', addCount,
            '' if addCount == totalCount else f' (排除 {totalCount - addCount} 份)'
        )
    }

async def autoSignUp(pageId: str, wsId: str, prop: typing.Any = None) -> dict:
    innerSession = serverMix.innerSession.get(pageId)
    if innerSession['runing']:
        return {
            'code': -1,
            'message': '工具執行中。',
        }

    if type(prop) != dict:
        return {
            'code': -1,
            'message': appUtils.console.getErrorMsg(
                appUtils.console.baseMsg, '_notExpectedType', 'prop', 'Object'
            ),
        }
    if not ('needCount' in prop and type(prop['needCount']) == int):
        return {
            'code': -1,
            'message': appUtils.console.getErrorMsg(
                appUtils.console.baseMsg, '_notExpectedType', 'prop.needCount'
            ),
        }
    elif prop['needCount'] < 1:
        return {
            'code': -1,
            'message': '"prop.needCount" must be greater than 1.',
        }

    innerSession['runing'] = True
    asyncio.ensure_future(_autoSignUpAction(pageId, innerSession, prop))
    return {
        'code': 0,
        'message': '請求已接收。'
    }

async def _autoSignUpAction(pageId: str, innerSession: dict, data: dict):
    logName = 'autoSignUpAction'
    try:
        groupPeer = novice.py_env['peers']['niUserChannle']

        needCount = data['needCount']

        runIdCode = random.randrange(1000000, 9999999)
        middleName = ''

        modemPoolTable = ModemPoolTable(_modemPoolDataFilePath)
        modemCardInfos = modemPoolTable.filter(states = ['NEVER', 'TRIED'])
        canScanCount = len(modemCardInfos)
        if needCount == None or canScanCount < needCount:
            needCount = canScanCount

        # 計算單次掃描數量
        scanTaskAmount = needCount * _scanTaskMultiple
        scanTaskMax = min(canScanCount, _scanTaskMax)
        if scanTaskAmount > scanTaskMax:
            scanTaskAmount = scanTaskMax

        tgAppMain = novice.py_env['tgApp']['main']
        apiId = tgAppMain['apiId']
        signUpTgSignUpTool = TgSignUpTool(
            apiId,
            tgAppMain['apiHash'],
            sessionPrefix = f'{_sessionDirPath}/telethon-{apiId}',
            sessionAddPrefix = 'autoSignUp',
            confirmTimeoutSec = _config_confirmTimeoutSec,
            inputTimeoutSec = _config_inputTimeoutSec,
            requestSmsTimeoutSec = _config_requestSmsTimeoutSec
        )

        nameList = utils.json.loadYml(_nameListFilePath)
        randomName = RandomName(nameList, middleName)

        shareStore = {
            'needCount': needCount,
            'canScanCount': canScanCount,
            'scanCount': 0,
            'successScanCount': 0,
            'successCount': 0,
        }

        isGetFloodWaitError = False
        try:
            runTasks = []
            for modemCardInfo in modemCardInfos:
                phoneNumber = modemCardInfo['phone']

                await _asyncLogSend(pageId, logName, {
                    'code': 1,
                    'message': appUtils.console.log(
                        runIdCode, _cindyAutoSignUpMessage, 'startWhichPhone',
                        phoneNumber
                    ),
                })

                runTasks.append(_autoSignUpHandle(
                    pageId, runIdCode, logName,
                    modemCardInfo, modemPoolTable,
                    signUpTgSignUpTool, randomName, groupPeer,
                    shareStore
                ))

                if len(runTasks) == scanTaskAmount:
                    await asyncio.gather(*runTasks)
                    runTasks.clear()

                    successCount = shareStore['successCount']
                    if successCount < needCount:
                        scanTaskAmount = (needCount - successCount) * _scanTaskMultiple
                        if scanTaskAmount > scanTaskMax:
                            scanTaskAmount = scanTaskMax
                    else:
                        break
            if len(runTasks) != 0:
                await asyncio.gather(*runTasks)
                runTasks.clear()
        except telethon.errors.FloodWaitError as err:
            waitTimeSec = err.seconds
            isCanWait = waitTimeSec < 180
            await _asyncLogSend(pageId, logName, {
                'code': 1 if isCanWait else -1,
                'message': appUtils.console.error(
                    runIdCode, _cindyAutoSignUpMessage, 'floodWait',
                    phoneNumber, waitTimeSec,
                    ' (waiting)' if isCanWait else ''
                ),
            })
            if isCanWait:
                await asyncio.sleep(waitTimeSec)
            else:
                isGetFloodWaitError = True
        except Exception as err:
            await _asyncLogSend(pageId, logName, {
                'code': -1,
                'message': appUtils.console.catchError(runIdCode, 'autoSignUp'),
            })

        scanPhoneCount = shareStore['scanCount']
        scanLastSuccessCount = shareStore['successScanCount']
        successCount = shareStore['successCount']
        modemPoolTable.gatherSmsScanInfo(
            scanPhoneCount, scanLastSuccessCount, canScanCount
        )
        modemPoolTable.gatherModemCardInfo()
        modemPoolTable.store()
        await _asyncLogSend(pageId, logName, {
            'code': -1,
            'message': appUtils.console.log(
                runIdCode, _cindyAutoSignUpMessage,
                *(('failedSignUp', scanPhoneCount) if successCount == 0 else \
                  ('successSignUp', scanPhoneCount, successCount)
                ),
                '' if successCount >= needCount else \
                    ' (FloodWaitError 警告)' if isGetFloodWaitError else \
                    ' (可註冊的用戶數量不足)' if scanLastSuccessCount == 0 else \
                    ' (請稍後再嘗試一次)' if successCount == 0 else \
                    ' (數量不足，請稍後再嘗試一次)'
            ),
        })
    except Exception as err:
        await _asyncLogSend(pageId, logName, {
            'code': -1,
            'message': appUtils.console.catchError(runIdCode, 'autoSignUpAction'),
        })
    finally:
        innerSession['runing'] = False

_cindyAddMessage = {
    # -1 程式錯誤
    'notExpectedModemCardLineFormat': '"{}" 不符合預期的格式。',
    # 1
    'successAddModemCards': '成功新增 {} 份貓卡名單。{}',
}

_cindyAutoSignUpMessage = {
    # -1 程式錯誤
    'notExpectedModemCardLineFormat': '"{}" 不符合預期的格式。',
    'failedSignUp': '共掃描 {} 張號碼但皆無法註冊。{}',
    # 1
    'startWhichPhone': '+{} Go',
    'connectBanned': '[{}]: +{} has been banned.',
    'connectOther': '[{}]: +{} skip. (無法使用自動化登入，狀態： {})',
    'signUpOther': '[{}]: +{} skip. (註冊失敗，狀態： {})',
    'autoSignUpStart': '[autoSignUpHandle]: 自動註冊開始',
    'autoSignUpConnectSendByApp': '[autoSignUpHandle]: +{} has been used.',
    'autoSignUpConnectPhoneInvalid': '[autoSignUpHandle]: +{} phone number is invalid.',
    'autoSignUpWhoami': '[autoSignUpHandle]: +{} 我是誰？',
    'autoSignUpConnectLogining': '[autoSignUpHandle]: +{} 已登入。',
    'autoSignUpEnough': '[autoSignUpHandle]: +{} 需求已飽和。',
    'autoSignUpGetSmsOk': '[autoSignUpHandle]: +{} 掃描確認可用。',
    'autoSignUpGetSmsOther': '[autoSignUpHandle]: +{} 無法取得簡訊驗證碼。',
    'autoSignUpOk': '[autoSignUpHandle]: +{} my name is {}.',
    'floodWait': '+{} get FloodWaitError: wait {} seconds.{}',
    # 2
    'successSignUp': '共掃描 {} 張號碼並成功註冊 {} 個仿用戶。{}',
}

class ModemPoolTable():
    def __init__(self, filePath: str):
        self.filePath = filePath

        self.data = utils.json.load(filePath) \
            if os.path.exists(filePath) else {}
        if not 'total' in self.data:
            self.data['total'] = 0
        if not 'statistic' in self.data:
            self.data['statistic'] = {}
        else:
            statisticData = self.data['statistic']
            if not 'modemCard' in statisticData:
                statisticData['modemCard'] = {}
            if not 'smsScan' in statisticData:
                statisticData['smsScan'] = []
        if not 'modemCardInfos' in self.data:
            self.data['modemCardInfos'] = []

        self.allPhones = allPhones = []
        for info in self.data['modemCardInfos']:
            allPhones.append(info['phone'])

    status = {
        'INVALID': 'invalid',
        'NEVER': 'never',
        'BANNED': 'banned',
        'TRIED': 'tried',
        'USED': 'used',
        'OK': 'ok',
        'OKBANNED': 'ok and then banned',
    }

    def addModemCard(self, phoneNumber: str, token: str, smsUrlFormat: str):
        self.allPhones.append(phoneNumber)
        self.data['modemCardInfos'].append({
            'state': self.status['NEVER'],
            'connectState': None,
            'phone': phoneNumber,
            'token': token,
            'smsUrl': smsUrlFormat.format(token = token),
            'name': '',
        })

    def store(self) -> None:
        utils.json.dump(self.data, self.filePath)

    def whichPhone(self, phoneNumber: str) -> typing.Union[None, dict]:
        if phoneNumber in self.allPhones:
            for info in self.data['modemCardInfos']:
                if info['phone'] == phoneNumber:
                    return info

        return None

    def filter(self, states: typing.Union[None, str, list] = None) -> list:
        if type(states) == str:
            filterStates = [states]
        elif type(states) == list:
            filterStates = states
        else:
            filterStates = []

        newList = []
        for info in self.data['modemCardInfos']:
            for stateKey in filterStates:
                if info['state'] == self.status[stateKey]:
                    newList.append(info)
                    break

        return newList

    def updateItem(self,
            modemCardInfo: dict,
            state: typing.Union[None, str] = None,
            connectStateTxt: typing.Union[None, str] = None,
            name: typing.Union[None, str] = None,
            isStore: bool = True):
        if state != None:
            modemCardInfo['state'] = self.status[state]
            modemCardInfo['connectState'] = connectStateTxt
        elif connectStateTxt != None:
            modemCardInfo['connectState'] = connectStateTxt

        if name != None:
            modemCardInfo['name'] = name

        if isStore:
            self.store()

    def gatherModemCardInfo(self) -> typing.Tuple[int, dict]:
        total = 0
        statisticInfo = {}
        for state in self.status:
            statisticInfo[self.status[state]] = 0

        for info in self.data['modemCardInfos']:
            total += 1
            statisticInfo[info['state']] += 1

        self.data['total'] = total
        self.data['statistic']['modemCard'] = statisticInfo

        return (total, statisticInfo)

    def gatherSmsScanInfo(self,
            scanCount: int,
            successCount: int,
            canScanCount: int) -> str:
        readableDtUtc = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ')

        successScanRate = math.floor(successCount / scanCount * 10000) / 100
        txt = f'{successCount}/{scanCount} ({successScanRate}%)'

        self.data['statistic']['smsScan'].append({
            'date': readableDtUtc,
            'scanCount': scanCount,
            'successCount': successCount,
            'canScanCount': canScanCount,
            'text': txt,
        })
        return txt

class TgSignUpTool():
    def __init__(self,
            apiId: str,
            apiHash: str,
            sessionPrefix: str,
            sessionAddPrefix: str = '',
            deviceModel: str = '',
            systemVersion: str = '',
            confirmTimeoutSec: float = 7,
            inputTimeoutSec: float = 7,
            requestSmsTimeoutSec: float = 30):
        self.apiId = apiId
        self.apiHash = apiHash
        self.sessionPrefix = sessionPrefix
        self.sessionAddPrefix = sessionAddPrefix

        sessionDirPath = os.path.dirname(sessionPrefix)
        if not os.path.exists(sessionDirPath):
            os.makedirs(sessionDirPath)

        platformUname = platform.uname()
        self.deviceModel = deviceModel \
            if deviceModel != '' else platformUname.machine
        self.systemVersion = systemVersion \
            if systemVersion != '' else platformUname.release
        # self.app_version = telethon.version.__version__

        self._confirmTimeoutSec = confirmTimeoutSec
        self._inputTimeoutSec = inputTimeoutSec

        self._sms_responseTimeoutSec = 9
        # "+3" 秒為處理的緩衝時間
        responseTimeoutSec = self._sms_responseTimeoutSec + 3
        smsTimeoutSec = requestSmsTimeoutSec \
            if responseTimeoutSec < requestSmsTimeoutSec else responseTimeoutSec
        # 每次發起請求介於 2 ~ 10 秒間
        runNextTimeSec = smsTimeoutSec / 5
        runNextTimeSec = 2 if runNextTimeSec < 2 \
            else runNextTimeSec if runNextTimeSec < 10 \
            else 10
        self._sms_timeoutSec = smsTimeoutSec
        self._sms_runNextTimeSec = runNextTimeSec
        self._sms_runNextWhenErrorTimeSec = runNextTimeSec * 1.5

    connectStatus = {
        'LOGINING': 'logining',
        'SENDBYSMS': 'send by sms',
        'SENDBYAPP': 'send by app',
        'SENDBYFLASHCall': 'send by flash call',
        'SENDBYCALL': 'send by call',
        'HASBANNED': 'has banned',
        'APIIDINVALID': 'API ID 無效',
        'PHONENUMBERFLOOD': '您請求代碼的次數過多',
        'PHONENUMBERINVALID': '電話號碼是無效的',
        'PHONEPASSWORDFLOOD': '您嘗試登錄太多次了',
        # 'OTHER': 'any message',
    }

    def getSessionPath(self,
            phoneNumber: str,
            addPrefix: str = '',
            noExt: bool = False) -> str:
        return '{}-{}{}'.format(
            self.sessionPrefix \
                + ('' if addPrefix == '' else '-' + addPrefix),
            phoneNumber,
            '' if noExt else '.session'
        )

    def mvSessionPath(self, phoneNumber: str, toAddPrifix: str = ''):
        sessionFilePathPart = self.sessionPrefix + phoneNumber
        fromPath = self.getSessionPath(phoneNumber, self.sessionAddPrefix)
        toPath = self.getSessionPath(phoneNumber, toAddPrifix)
        if os.path.exists(fromPath):
            os.rename(fromPath, toPath)

    async def connect(self,
            phoneNumber: str
            ) -> typing.Tuple[str, typing.Union[None, TelegramClient], str]:
        sessionFilePathPart = self.getSessionPath(
            phoneNumber, self.sessionAddPrefix, True
        )
        client = TelegramClient(
            sessionFilePathPart,
            self.apiId,
            self.apiHash,
            device_model = self.deviceModel,
            system_version = self.systemVersion
        )

        try:
            await client.connect()
        except Exception as err:
            raise Exception(f'from client.connect() failed {type(err)} Error: {err}')

        if await client.is_user_authorized():
            return (self.connectStatus['LOGINING'], client, '')

        appUtils.console.logMsg(
            '---',
            f'[TgSignUpTool.connect]: +{phoneNumber} send request.'
        )
        try:
            sendCode = await client.send_code_request(phoneNumber)
        except telethon.errors.ApiIdInvalidError as err:
            raise Exception(self.connectStatus['APIIDINVALID'])
        except telethon.errors.PhoneNumberBannedError as err:
            return (self.connectStatus['HASBANNED'], None, '')
        except telethon.errors.PhoneNumberFloodError as err:
            return (self.connectStatus['PHONENUMBERFLOOD'], None, '')
        except telethon.errors.PhoneNumberInvalidError as err:
            return (self.connectStatus['PHONENUMBERINVALID'], None, '')
        except telethon.errors.PhonePasswordFloodError as err:
            return (self.connectStatus['PHONEPASSWORDFLOOD'], None, '')
        except telethon.errors.FloodWaitError as err:
            raise err
        except Exception as err:
            raise Exception(
                f'from client.send_code_request() failed {type(err)} Error: {err}'
            )

        phoneCodeHash = sendCode.phone_code_hash
        sentCodeType = type(sendCode.type)
        if sentCodeType == telethon.types.auth.SentCodeTypeSms:
            return (self.connectStatus['SENDBYSMS'], client, phoneCodeHash)
        elif sentCodeType == telethon.types.auth.SentCodeTypeApp:
            return (self.connectStatus['SENDBYAPP'], client, phoneCodeHash)
        elif sentCodeType == telethon.types.auth.SentCodeTypeFlashCall:
            return (self.connectStatus['SENDBYFLASHCall'], client, phoneCodeHash)
        elif sentCodeType == telethon.types.auth.SentCodeTypeCall:
            return (self.connectStatus['SENDBYCALL'], client, phoneCodeHash)
        else:
            return (f'send by {sentCodeType.__name__}', client, phoneCodeHash)

    requestSmsStatus = {
        'OK': 'ok',
        'SKIP': 'can not get sms and skip',
    }

    async def getSmsVerifiedCode(
            self,
            phoneNumber: str,
            smsUrl: str) -> typing.Tuple[str, str]:
        runNextTimeSec = self._sms_runNextTimeSec
        runNextWhenErrorTimeSec = self._sms_runNextWhenErrorTimeSec

        waitOnceTimedelta = datetime.timedelta(seconds = self._sms_timeoutSec)
        dtStart = datetime.datetime.now()

        # NOTE: 可能有過往殘存紀錄，所以先等一下下。
        await asyncio.sleep(runNextTimeSec)

        while True:
            nextTimeSec = runNextTimeSec

            isStatusCode200 = False
            try:
                response = requests.get(smsUrl, timeout = 12)
                if response.status_code == 200:
                    isStatusCode200 = True
                else:
                    nextTimeSec = runNextWhenErrorTimeSec
            except Exception as err:
                nextTimeSec = runNextWhenErrorTimeSec

            if isStatusCode200:
                smsData = response.json()
                smsMsg = smsData['message']

                if smsData['flag'] or len(smsData['data']) > 0:
                    appUtils.console.logMsg(
                        '---',
                        '[TgSignUpTool.getSmsVerifiedCode]:'
                            f' +{phoneNumber} smsData 1: {smsData}.'
                    )

                if smsMsg != 'No has message':
                    appUtils.console.logMsg(
                        '---',
                        '[TgSignUpTool.getSmsVerifiedCode]:'
                            f' +{phoneNumber} smsData 2: {smsData}.'
                    )
                    verifiedCode = self._parseSmsMsg(smsMsg)
                    if verifiedCode != None:
                        return (self.requestSmsStatus['OK'], verifiedCode)
                    else:
                        appUtils.console.logMsg(
                            '---',
                            '[TgSignUpTool.getSmsVerifiedCode]:'
                                f' +{phoneNumber} get message: {smsMsg}.'
                        )
                        return (self.requestSmsStatus['SKIP'], '')

            timedelta = datetime.datetime.now() - dtStart
            if timedelta > waitOnceTimedelta:
                return (self.requestSmsStatus['SKIP'], '')
            else:
                await asyncio.sleep(nextTimeSec)

    def _parseSmsMsg(self, smsMsg: str) -> typing.Union[None, str]:
        matchTgCode = re.search(self._parseSmsMsg_regeTgCode, smsMsg)

        if not matchTgCode:
            return None

        tgCode = matchTgCode.group(1)
        return tgCode

    _parseSmsMsg_regeTgCode = r'^(?:t|T)elegram code (\d{5})'

    signUpStatus = {
        'OK': 'ok',
        'PHONECODEINVALID': '驗證碼錯誤',
        'SESSIONPASSWORDNEEDED': '需要二次驗證',
        'PHONECODEEMPTY': '驗證碼丟失',
        'PHONECODEEXPIRED': '驗證碼已過期',
        'PHONENUMBERINVALID': '電話號碼是無效的',
        'FIRSTNAMEINVALID': '名字無效',
        'MEMBEROCCUPYPRIMARYLOCFAILED': 'Occupation of primary member location failed.',
        'PHONENUMBERFLOOD': '您請求代碼的次數過多',
        'PHONENUMBEROCCUPIED': '該電話號碼已被使用',
        'REGIDGENERATEFAILED': '生成註冊 ID 時失敗',
        # 'OTHER': 'any message',
    }

    async def signUp(self,
            client: TelegramClient,
            phoneNumber: str,
            verifiedCode: str,
            phoneCodeHash: str,
            firstName: str,
            lastName: str) -> str:
        appUtils.console.logMsg(
            '---',
            f'[TgSignUpTool.signUp]: +{phoneNumber} verify verifiedCode.'
        )
        try:
            await client.sign_in(
                code = verifiedCode,
                phone_code_hash = phoneCodeHash
            )
        except telethon.errors.PhoneCodeInvalidError:
            return self.signUpStatus['PHONECODEINVALID']
        except telethon.errors.PhoneNumberUnoccupiedError:
            pass
        except telethon.errors.SessionPasswordNeededError:
            return self.signUpStatus['SESSIONPASSWORDNEEDED']
        except telethon.errors.PhoneCodeEmptyError as err:
            return self.signUpStatus['PHONECODEEMPTY']
        except telethon.errors.PhoneCodeExpiredError as err:
            return self.signUpStatus['PHONECODEEXPIRED']
        except telethon.errors.PhoneNumberInvalidError as err:
            return self.signUpStatus['PHONENUMBERINVALID']
        except Exception as err:
            return f'from client.sign_in() failed {type(err)} Error: {err}'

        appUtils.console.logMsg(
            '---',
            f'[TgSignUpTool.signUp]: +{phoneNumber} sign up.'
        )
        try:
            await client.sign_up(
                verifiedCode,
                firstName,
                lastName,
                phone_code_hash = phoneCodeHash
            )
        except telethon.errors.FirstNameInvalidError:
            return self.signUpStatus['FIRSTNAMEINVALID']
        except telethon.errors.PhoneCodeInvalidError:
            return self.signUpStatus['PHONECODEINVALID']
        except telethon.errors.MemberOccupyPrimaryLocFailedError:
            return self.signUpStatus['MEMBEROCCUPYPRIMARYLOCFAILED']
        except telethon.errors.PhoneCodeEmptyError:
            return self.signUpStatus['PHONECODEEMPTY']
        except telethon.errors.PhoneCodeExpiredError as err:
            return self.signUpStatus['PHONECODEEXPIRED']
        except telethon.errors.PhoneNumberFloodError as err:
            return self.connectStete['PHONENUMBERFLOOD']
        except telethon.errors.PhoneNumberInvalidError as err:
            return self.connectStete['PHONENUMBERINVALID']
        except telethon.errors.PhoneNumberOccupiedError as err:
            return self.connectStete['PHONENUMBEROCCUPIED']
        except telethon.errors.RegIdGenerateFailedError as err:
            return self.connectStete['REGIDGENERATEFAILED']
        except Exception as err:
            return f'from client.sign_up() failed {type(err)} Error: {err}'

        try:
            files = os.listdir(_photoDirPath)
            indexStart = random.randrange(0, len(files) - 1)
            await client(telethon.functions.photos.UploadProfilePhotoRequest(
                await client.upload_file(_photoDirPath + '/' + files[indexStart])
            ))
        except Exception as err:
            appUtils.console.catchErrorMsg('---', f'{type(err)} Error: {err}')

        return self.signUpStatus['OK']

    async def getMyName(self, client: TelegramClient) -> typing.Union[None, str]:
        meInfo = await client.get_me()
        if meInfo == None:
            return None
        return f'{meInfo.first_name} {meInfo.last_name}'

    async def sayHi(self,
            client: TelegramClient,
            groupPeer: str,
            txt: str = '') -> telethon.types.Updates:
        realUserName, isPrivate = telethon.utils.parse_username(groupPeer)
        if isPrivate:
            await client(
                telethon.functions.messages.ImportChatInviteRequest(realUserName)
            )
        else:
            await client(telethon.functions.channels.JoinChannelRequest(
                channel = groupPeer
            ))

        return await client(telethon.functions.messages.SendMessageRequest(
            peer = groupPeer,
            message = 'Hi{}'.format(f', {txt}' if txt != '' else ''),
            random_id = random.randrange(1000000, 9999999)
        ))

    callNiUserStatus = {
        'WHOAMI': 'who am I ?',
        'NOTPRESENT': '未到場',
        'OK': 'ok',
    }

    # 招喚仿用戶
    async def callNiUser(self,
            client: TelegramClient,
            groupPeer: str,
            message: str = '') -> typing.Tuple[
                str,
                typing.Union[None, str],
                typing.Union[None, Exception, telethon.types.Updates]
            ]:
        myName = await self.getMyName(client)
        if myName == None:
            return (self.callNiUserStatus['WHOAMI'], None, None)

        try:
            update = await self.sayHi(client, groupPeer, message)
            return (self.callNiUserStatus['OK'], myName, update)
        except Exception as err:
            return (self.callNiUserStatus['NOTPRESENT'], myName, err)

class RandomName():
    def __init__(self, nameList: dict, lastPrefix: str = ''):
        self._nameList = nameList
        self._nameListLength = len(nameList)
        self._lastPrefix = lastPrefix

    def getOne(self) -> str:
        return self._nameList[random.randrange(0, self._nameListLength)]

    def get(self) -> typing.Tuple[str, str, str]:
        firstName = self.getOne()
        lastName = self._lastPrefix + self.getOne()
        return (firstName + ' ' + lastName, firstName, lastName)

async def _asyncLogSend(pageId: str, name: str, result: typing.Any):
    await serverMix.wsHouse.send(pageId, fnResult = {
        'name': f'cindy.{name}',
        'result': result,
    })


async def _autoSignUpHandle(
        pageId: str,
        runIdCode: str,
        logName: str,
        modemCardInfo: dict,
        modemPoolTable: ModemPoolTable,
        tgSignUpTool: TgSignUpTool,
        randomName: RandomName,
        groupPeer: str,
        shareStore: dict):
    await _asyncLogSend(pageId, logName, {
        'code': 1,
        'message': appUtils.console.log(
            runIdCode, _cindyAutoSignUpMessage, 'autoSignUpStart'
        ),
    })

    phoneNumber = modemCardInfo['phone']
    smsUrl = modemCardInfo['smsUrl']

    scanGetErrorMsg = 'signUp-scan get error: '
    signUpGetErrorMsg = 'signUp get error: '

    shareStore['scanCount'] += 1
    try:
        connectStete, client, phoneCodeHash = await tgSignUpTool.connect(phoneNumber)
    except Exception as err:
        modemPoolTable.updateItem(
            modemCardInfo,
            state = 'TRIED',
            connectStateTxt = f'{scanGetErrorMsg}{err}'
        )
        if type(err) == telethon.errors.FloodWaitError:
            tgSignUpTool.mvSessionPath(phoneNumber, 'autoSignUpRm')
        else:
            tgSignUpTool.mvSessionPath(phoneNumber, 'autoSignUpErr')
        raise err

    if connectStete != TgSignUpTool.connectStatus['SENDBYSMS']:
        # 資料有誤，需更新資料
        if connectStete == TgSignUpTool.connectStatus['LOGINING']:
            isSuccess = _autoSignUpHandle_callNiUser(
                pageId, runIdCode, logName,
                modemCardInfo, modemPoolTable,
                tgSignUpTool,
                client, groupPeer,
                isHasLogined = True
            )
            await _asyncLogSend(pageId, logName, {
                'code': 1,
                'message': appUtils.console.log(
                    runIdCode, _cindyAutoSignUpMessage,
                    'autoSignUpConnectLogining', phoneNumber
                    ),
            })
            if isSuccess:
                shareStore['successCount'] += 1
                tgSignUpTool.mvSessionPath(phoneNumber, '')
            else:
                tgSignUpTool.mvSessionPath(phoneNumber, 'whoami')
                await _asyncLogSend(pageId, logName, {
                    'code': 1,
                    'message': appUtils.console.log(
                        runIdCode, _cindyAutoSignUpMessage,
                        'autoSignUpWhoami', phoneNumber
                    ),
                })
        elif connectStete == TgSignUpTool.connectStatus['HASBANNED']:
            modemPoolTable.updateItem(modemCardInfo, state = 'BANNED')
            tgSignUpTool.mvSessionPath(phoneNumber, 'autoSignUpRm')
            await _asyncLogSend(pageId, logName, {
                'code': 1,
                'message': appUtils.console.log(
                    runIdCode, _cindyAutoSignUpMessage,
                    'connectBanned', 'autoSignUpHandle', phoneNumber
                ),
            })
        elif connectStete == TgSignUpTool.connectStatus['SENDBYAPP']:
            modemPoolTable.updateItem(modemCardInfo, state = 'USED')
            tgSignUpTool.mvSessionPath(phoneNumber, 'autoSignUpRm')
            await _asyncLogSend(pageId, logName, {
                'code': 1,
                'message': appUtils.console.log(
                    runIdCode, _cindyAutoSignUpMessage,
                    'autoSignUpConnectSendByApp', phoneNumber
                ),
            })
        elif connectStete == TgSignUpTool.connectStatus['PHONENUMBERINVALID']:
            modemPoolTable.updateItem(
                modemCardInfo,
                state = 'INVALID',
                connectStateTxt = connectStete
            )
            tgSignUpTool.mvSessionPath(phoneNumber, 'autoSignUpRm')
            await _asyncLogSend(pageId, logName, {
                'code': 1,
                'message': appUtils.console.log(
                    runIdCode, _cindyAutoSignUpMessage,
                    'autoSignUpConnectPhoneInvalid', phoneNumber
                ),
            })
        else:
            modemPoolTable.updateItem(
                modemCardInfo,
                state = 'INVALID',
                connectStateTxt = f'{scanGetErrorMsg}{connectStete}'
            )
            tgSignUpTool.mvSessionPath(phoneNumber, 'autoSignUpRm')
            await _asyncLogSend(pageId, logName, {
                'code': 1,
                'message': appUtils.console.log(
                    runIdCode, _cindyAutoSignUpMessage,
                    'connectOther', 'autoSignUpHandle', phoneNumber, connectStete
                ),
            })

        if client != None:
            await client.disconnect()
        return

    isNotRecordScanSuccess = True
    fullName, firstName, lastName = randomName.get()
    for loopTimes in range(1, -1, -1):
        if shareStore['successCount'] >= shareStore['needCount']:
            await _asyncLogSend(pageId, logName, {
                'code': 1,
                'message': appUtils.console.log(
                    runIdCode, _cindyAutoSignUpMessage, 'autoSignUpEnough', phoneNumber
                ),
            })
            break

        requestSmsState, verifiedCode = await tgSignUpTool.getSmsVerifiedCode(
            phoneNumber, smsUrl
        )
        if requestSmsState != TgSignUpTool.requestSmsStatus['OK']:
            modemPoolTable.updateItem(
                modemCardInfo,
                state = 'INVALID',
                connectStateTxt = f'{scanGetErrorMsg}{requestSmsState}'
            )
            tgSignUpTool.mvSessionPath(phoneNumber, 'autoSignUpErr')
            await _asyncLogSend(pageId, logName, {
                'code': 1,
                'message': appUtils.console.log(
                    runIdCode, _cindyAutoSignUpMessage,
                    'autoSignUpGetSmsOther', phoneNumber
                ),
            })
            break

        if isNotRecordScanSuccess:
            isNotRecordScanSuccess = False
            shareStore['successScanCount'] += 1
            await _asyncLogSend(pageId, logName, {
                'code': 1,
                'message': appUtils.console.log(
                    runIdCode, _cindyAutoSignUpMessage, 'autoSignUpGetSmsOk',
                    phoneNumber
                ),
            })

        if shareStore['successCount'] >= shareStore['needCount']:
            await _asyncLogSend(pageId, logName, {
                'code': 1,
                'message': appUtils.console.log(
                    runIdCode, _cindyAutoSignUpMessage, 'autoSignUpEnough', phoneNumber
                ),
            })
            break

        signUpStete = await tgSignUpTool.signUp(
            client, phoneNumber, verifiedCode, phoneCodeHash, firstName, lastName
        )

        if signUpStete == TgSignUpTool.signUpStatus['OK']:
            modemPoolTable.updateItem(
                modemCardInfo,
                state = 'OK',
                name = f'{fullName} (unconfirmed)'
            )

            isSuccess = await _autoSignUpHandle_callNiUser(
                modemCardInfo, modemPoolTable,
                tgSignUpTool,
                client, groupPeer, fullName
            )
            if isSuccess:
                await _asyncLogSend(pageId, logName, {
                    'code': 1,
                    'message': appUtils.console.log(
                        runIdCode, _cindyAutoSignUpMessage,
                        'autoSignUpOk', phoneNumber, fullName
                    ),
                })
                shareStore['successCount'] += 1
                tgSignUpTool.mvSessionPath(phoneNumber, '')
                await niUsersStatusUpdateStatus(allCount = 1, usableCount = 1)
            else:
                tgSignUpTool.mvSessionPath(phoneNumber, 'whoami')
                await _asyncLogSend(pageId, logName, {
                    'code': 1,
                    'message': appUtils.console.log(
                        runIdCode, _cindyAutoSignUpMessage,
                        'autoSignUpWhoami', phoneNumber
                    ),
                })
            break

        if loopTimes > 0 and (
                    signUpStete == TgSignUpTool.signUpStatus['PHONECODEINVALID'] \
                    or signUpStete == TgSignUpTool.signUpStatus['PHONECODEEMPTY'] \
                    or signUpStete == TgSignUpTool.signUpStatus['PHONECODEEXPIRED']
                ):
            continue

        modemPoolTable.updateItem(
            modemCardInfo,
            state = 'INVALID',
            connectStateTxt = f'{signUpGetErrorMsg}{signUpStete}'
        )
        tgSignUpTool.mvSessionPath(phoneNumber, 'autoSignUpErr')
        await _asyncLogSend(pageId, logName, {
            'code': 1,
            'message': appUtils.console.log(
                runIdCode, _cindyAutoSignUpMessage,
                'signUpOther', 'autoSignUpHandle', phoneNumber, signUpStete
            ),
        })
        break

    await client.disconnect()

async def _autoSignUpHandle_callNiUser(
        modemCardInfo: dict,
        modemPoolTable: ModemPoolTable,
        tgSignUpTool: TgSignUpTool,
        client: TelegramClient,
        groupPeer: str,
        fullName: str = '',
        isHasLogined: bool = False) -> bool:
    fullName = '---(has logined)' if isHasLogined else fullName
    sayTxt = 'Do you miss me ?' if isHasLogined else f'I\'m {fullName}'
    callNiUserState, niUserName, sayHiUpdate \
        = await tgSignUpTool.callNiUser(client, groupPeer, sayTxt)

    if callNiUserState == TgSignUpTool.callNiUserStatus['WHOAMI']:
        modemPoolTable.updateItem(
            modemCardInfo,
            state = 'INVALID',
            name = f'{fullName} (who am I ?)'
        )
        return False

    modemPoolTable.updateItem(modemCardInfo, state = 'OK', name = f'{niUserName}')
    return True

