#!/usr/bin/env python3


import pdb
import typing
import os
import sys
import platform
import math
import random
import time
import datetime
import re
import asyncio
import select
import requests
import telethon as telethon
import utils.json
import utils.novice as novice


TelegramClient = telethon.TelegramClient

_sessionDirPath = novice.py_dirname + '/' + novice.py_env['tgSessionDirPath']
_envModemPool = novice.py_env['modemPool']
_modemPoolDataFilePath = novice.py_dirname + '/' + _envModemPool['dataFilePath']
_nameListFilePath = novice.py_dirname + '/' + _envModemPool['nameListFilePath']

_scanTaskMultiple = 3 # 使用需求數的 X 倍數同時掃描
_scanTaskMax = 20 # 單次同時掃描的最大值
_config_confirmTimeoutSec = 0.1
_config_inputTimeoutSec = 0.1
_config_requestSmsTimeoutSec = 0.1


async def asyncRun(args: list, _dirpy: str, _dirname: str):
    addUsageTxt = 'add <modemCardsFilePath>'
    smsScanUsageTxt = 'smsScan [needCount (n > 0)]'
    autoSignUpUsageTxt = 'autoSignUp <groupPeer> [<needCount (n > 0)> [middleName]]'
    checkOkUsageTxt = 'checkOk'

    argsLength = len(args)
    if argsLength > 1:
        method = args[1]
        if method == 'add':
            if argsLength < 3:
                raise ValueError(f'Usage: {addUsageTxt}')

            _run_add(args[2])
            return

        if not os.path.exists(_modemPoolDataFilePath):
            raise Exception(f'Not found "{_modemPoolDataFilePath}" file.')

        if method == 'smsScan':
            needCount = None if argsLength < 3 else int(args[2])
            await _run_smsScan(needCount)
            return
        elif method == 'autoSignUp':
            if argsLength < 3:
                raise ValueError(f'Usage: {autoSignUpUsageTxt}')

            groupPeer = args[2]
            needCount = None if argsLength < 4 else int(args[3])
            middleName = '' if argsLength < 5 else args[4]
            await _run_autoSignUp(groupPeer, needCount, middleName)
            return
        elif method == 'checkOk':
            await _run_checkOk()
            return

    print(
        f'Usage: {addUsageTxt}\n'
        f'       {smsScanUsageTxt}\n'
        f'       {autoSignUpUsageTxt}\n'
        f'       {checkOkUsageTxt}'
    )
    os._exit(1)

def _run_add(modemCardsFilePath: str):
    with open(modemCardsFilePath, 'r', encoding = 'utf-8') as fs:
        smsUrlFormat = _envModemPool['smsUrlFormat']

        modemPoolTable = ModemPoolTable(_modemPoolDataFilePath)
        regeCindyVoipTxt = r'^(\d+)\|([0-9a-fA-F]+)\n$'

        totalCount = 0
        addCount = 0
        lines = fs.readlines()
        for line in lines:
            totalCount += 1
            matchTgCode = re.search(regeCindyVoipTxt, line)

            if not matchTgCode:
                raise Exception(f'不符合預期的格式 ({line})')

            phone = matchTgCode.group(1)
            token = matchTgCode.group(2)

            modemCardInfo = modemPoolTable.whichPhone('1' + phone)
            if modemCardInfo != None and token == modemCardInfo['token']:
                continue

            addCount += 1
            modemPoolTable.addModemCard('1' + phone, token, smsUrlFormat)

        modemPoolTable.gatherModemCardInfo()
        modemPoolTable.store()
        print(
            f'成功新增 {addCount} 份貓卡名單。'
            + ('' if addCount == totalCount else f' (排除 {totalCount - addCount} 份)')
        )

async def _run_smsScan(needCount: typing.Union[None, int]):
    modemPoolTable = ModemPoolTable(_modemPoolDataFilePath)
    if needCount != None and not needCount > 0:
        raise ValueError(f'"needCount" must be a integer greater than 1.')

    tgAppNotifyAndCheck = novice.py_env['tgApp']['notifyAndCheck']
    apiId = tgAppNotifyAndCheck['apiId']
    scanTgSignUpTool = TgSignUpTool(
        apiId,
        tgAppNotifyAndCheck['apiHash'],
        sessionPrefix = f'{_sessionDirPath}/notifyAndCheck/telethon-{apiId}',
        sessionAddPrefix = 'scan',
        confirmTimeoutSec = _config_confirmTimeoutSec,
        inputTimeoutSec = _config_inputTimeoutSec,
        requestSmsTimeoutSec = _config_requestSmsTimeoutSec
    )

    try:
        scanInfo = await _smsScan(modemPoolTable, scanTgSignUpTool, needCount)
    except Exception as err:
        raise err

    scanInfoTxt = modemPoolTable.gatherSmsScanInfo(
        scanInfo['scanCount'],
        scanInfo['successCount']
    )
    modemPoolTable.gatherModemCardInfo()
    modemPoolTable.store()
    print(f'[run_smsScan]: 成功掃描率 {scanInfoTxt}。')

async def _run_autoSignUp(
        groupPeer: str,
        needCount: typing.Union[None, int],
        middleName: str):
    modemPoolTable = ModemPoolTable(_modemPoolDataFilePath)
    if needCount != None and not needCount > 0:
        raise ValueError(f'"needCount" must be a integer greater than 1.')

    tgAppNotifyAndCheck = novice.py_env['tgApp']['notifyAndCheck']
    apiId = tgAppNotifyAndCheck['apiId']
    scanTgSignUpTool = TgSignUpTool(
        apiId,
        tgAppNotifyAndCheck['apiHash'],
        sessionPrefix = f'{_sessionDirPath}/notifyAndCheck/telethon-{apiId}',
        sessionAddPrefix = 'scan',
        confirmTimeoutSec = _config_confirmTimeoutSec,
        inputTimeoutSec = _config_inputTimeoutSec,
        requestSmsTimeoutSec = _config_requestSmsTimeoutSec
    )

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

    try:
        currNeedCount = needCount
        scanLastSuccessCount = 0
        scanPhones = []
        singUpInfo = {
            'needCount': needCount,
            'successCount': 0,
        }
        for loopTimes in range(1, 4):
            if loopTimes > 1:
                print(f'第 {loopTimes} 次嘗試自動註冊。')

            scanInfo = await _smsScan(
                modemPoolTable, scanTgSignUpTool, currNeedCount,
                shareStore = {
                    'scanPhones': scanPhones,
                }
            )
            scanLastSuccessCount = scanInfo['successCount']
            scanPhones = [*scanPhones, *scanInfo['scanPhones']]

            # 沒有可註冊的用戶
            if scanLastSuccessCount == 0:
                break

            modemPoolTable.gatherSmsScanInfo(
                scanInfo['scanCount'],
                scanLastSuccessCount
            )

            runTasks = []
            for modemCardInfo in scanInfo['successModemCardInfos']:
                runTasks.append(_autoSignUpHandle(
                    modemCardInfo, modemPoolTable,
                    signUpTgSignUpTool, randomName, groupPeer,
                    singUpInfo
                ))
            await asyncio.gather(*runTasks)
            runTasks.clear()

            successCount = singUpInfo['successCount']
            if successCount < currNeedCount:
                currNeedCount = needCount - successCount
            else:
                break

        scanPhoneCount = len(scanPhones)
        successCount = singUpInfo['successCount']
        if successCount == 0:
            print(
                f'共掃描 {scanPhoneCount} 張號碼但皆無法註冊。'
                ' (可註冊的用戶數量不足)' if scanLastSuccessCount == 0 else \
                    ' (請稍後再嘗試一次)'
            )
        else:
            print(
                f'共掃描 {scanPhoneCount} 張號碼並成功註冊 {successCount} 個仿用戶。'
                '' if successCount >= currNeedCount else \
                    ' (可註冊的用戶數量不足)' if scanLastSuccessCount == 0 else \
                    ' (數量不足，請稍後再嘗試一次)'
            )

        modemPoolTable.gatherModemCardInfo()
        modemPoolTable.store()
    except Exception as err:
        raise err

    if singUpInfo['successCount'] < needCount:
        print(
            '[run_autoSignUp]: 可註冊數量不足，'
            f'合計註冊 {singUpInfo["successCount"]} 位仿用戶。'
        )
    else:
        print(f'[run_autoSignUp]: 成功註冊 {singUpInfo["successCount"]} 位仿用戶。')

async def _run_checkOk():
    confirmTimeoutSec = _config_confirmTimeoutSec
    modemPoolTable = ModemPoolTable(_modemPoolDataFilePath)

    tgAppMain = novice.py_env['tgApp']['main']
    apiId = tgAppMain['apiId']
    tgSignUpTool = TgSignUpTool(
        apiId,
        tgAppMain['apiHash'],
        sessionPrefix = f'{_sessionDirPath}/telethon-{apiId}'
    )

    modemCardInfos = modemPoolTable.filter(states = ['OK'])
    shareStore = {
        'checkCount': len(modemCardInfos),
        'activeCount': 0,
        'exitedCount': 0,
    }
    runTasks = []
    for modemCardInfo in modemCardInfos:
        phoneNumber = modemCardInfo['phone']

        sessionFilePath = tgSignUpTool.getSessionPath(phoneNumber)
        if not os.path.exists(sessionFilePath):
            print(f'[run_checkOk]: +{phoneNumber} 找不到 "{sessionFilePath}" 文件。')

        isTimeout, _ = _inputTimeout(
            confirmTimeoutSec,
            f'[run_checkOk]: +{phoneNumber}'
            f' Go (pass <ENTER> or wait {confirmTimeoutSec} seconds to continue)'
        )
        if isTimeout:
            print()

        runTasks.append(
            _checkOkHandle(modemCardInfo, modemPoolTable, tgSignUpTool, shareStore)
        )

    await asyncio.gather(*runTasks)
    runTasks.clear()

    print(
        '[run_checkOk]:'
        f' check: {shareStore["checkCount"]},'
        f' active: {shareStore["activeCount"]},'
        f' exited: {shareStore["exitedCount"]}'
    )


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

    def gatherSmsScanInfo(self, scanCount: int, successCount: int) -> str:
        readableDtUtc = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ')

        successScanRate = math.floor(successCount / scanCount * 10000) / 100
        canScanCount = len(self.filter(states = ['NEVER', 'TRIED']))
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

        print(f'[TgSignUpTool.connect]: +{phoneNumber} send request.')
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
        confirmTimeoutSec = self._confirmTimeoutSec
        inputTimeoutSec = self._inputTimeoutSec

        runNextTimeSec = self._sms_runNextTimeSec
        runNextWhenErrorTimeSec = self._sms_runNextWhenErrorTimeSec

        waitTotalTimedelta = datetime.timedelta(seconds = 0)
        waitOnceTimedelta = datetime.timedelta(seconds = self._sms_timeoutSec)
        dtStart = datetime.datetime.now()

        # NOTE: 可能有過往殘存紀錄，所以先等一下下。
        await asyncio.sleep(runNextTimeSec)

        while True:
            sys.stdout.write('.')
            sys.stdout.flush()

            nextTimeSec = runNextTimeSec

            isStatusCode200 = False
            try:
                response = requests.get(smsUrl, timeout = 12)
                if response.status_code == 200:
                    isStatusCode200 = True
                else:
                    print(
                        f'\nfrom requests.get() failed +{phoneNumber} sms url'
                        f' response {response.status_code} status code.'
                    )
                    nextTimeSec = runNextWhenErrorTimeSec
            except Exception as err:
                print(
                    f'\nfrom requests.get() failed +{phoneNumber} sms url'
                    f' get {type(err)} Error: {err}.'
                )
                nextTimeSec = runNextWhenErrorTimeSec

            if isStatusCode200:
                smsData = response.json()
                smsMsg = smsData['message']

                isPrint = False
                if smsData['flag'] or len(smsData['data']) > 0:
                    isPrint = True
                    print(
                        '\n[TgSignUpTool.getSmsVerifiedCode]:'
                        f' +{phoneNumber} smsData 1: {smsData}.'
                    )

                if smsMsg != 'No has message':
                    if not isPrint:
                        print()
                    print(
                        '[TgSignUpTool.getSmsVerifiedCode]:'
                        f' +{phoneNumber} smsData 2: {smsData}.'
                    )
                    verifiedCode = self._parseSmsMsg(smsMsg)
                    if verifiedCode != None:
                        print(
                            '[TgSignUpTool.getSmsVerifiedCode]:'
                            f' +{phoneNumber} verifiedCode: {verifiedCode}.'
                        )
                        return (self.requestSmsStatus['OK'], verifiedCode)
                    else:
                        print(
                            '[TgSignUpTool.getSmsVerifiedCode]:'
                            f' +{phoneNumber} get message: {smsMsg}.'
                        )

                        isTimeout, verifiedCodeInput = _inputTimeout(
                            inputTimeoutSec,
                            f'[TgSignUpTool.get]: +{phoneNumber} input verified code'
                            ' (pass <ENTER> continue waiting or input "skip" to skip'
                            f' (default, or wait {inputTimeoutSec} seconds to skip)'
                            '): '
                        )
                        if isTimeout:
                            print()
                            verifiedCodeInput = 'skip'

                        if verifiedCodeInput == 'skip':
                            return (self.requestSmsStatus['SKIP'], '')
                        elif verifiedCodeInput != '':
                            return (self.requestSmsStatus['OK'], verifiedCodeInput)

            timedelta = datetime.datetime.now() - dtStart
            if timedelta > waitOnceTimedelta:
                waitTotalTimedelta += timedelta
                waitTimeMinute \
                    = math.floor(waitTotalTimedelta.total_seconds() / 60 * 10) / 10
                isTimeout, inputTxt = _inputTimeout(
                    confirmTimeoutSec,
                    '\n[TgSignUpTool.getSmsVerifiedCode]:'
                    f' +{phoneNumber} 已超過 {waitTimeMinute} 分鐘，是否還要繼續' \
                    f' (默認跳過，或者等待 {confirmTimeoutSec} 秒後自動跳過) ? [Y/N]: '
                )
                if isTimeout:
                    print()
                    continueInput = 'no'
                else:
                    continueInput = _inputYesOrNo(inputTxt)

                if continueInput == 'yes':
                    dtStart = datetime.datetime.now()
                else:
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
        print(f'[TgSignUpTool.signUp]: +{phoneNumber} verify verifiedCode.')
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

        print(f'[TgSignUpTool.signUp]: +{phoneNumber} sign up.')
        try:
            await client.sign_up(
                verifiedCode,
                firstName,
                lastName,
                phone_code_hash = phoneCodeHash
            )
            print()
            # 成功的話會出現下列訊息 :
            # By signing up for Telegram, you agree not to:
            #
            # - Use our service to send spam or scam users.
            # - Promote violence on publicly viewable Telegram bots, groups or channels.
            # - Post pornographic content on publicly viewable Telegram bots, groups or channels.
            #
            # We reserve the right to update these Terms of Service later.

            return self.signUpStatus['OK']
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

async def _smsScan(
        modemPoolTable: ModemPoolTable,
        tgSignUpTool: TgSignUpTool,
        needCount: typing.Union[None, int],
        shareStore: typing.Union[None, dict] = None) -> dict:
    confirmTimeoutSec = _config_confirmTimeoutSec

    modemCardInfos = modemPoolTable.filter(states = ['NEVER', 'TRIED'])
    modemCardInfosLength = len(modemCardInfos)
    if needCount == None or modemCardInfosLength < needCount:
        needCount = modemCardInfosLength

    scanTaskMultiple = _scanTaskMultiple
    scanTaskMax = min(modemCardInfosLength, _scanTaskMax)

    if shareStore == None:
        shareStore = {
            'needCount': needCount,
            'scanCount': 0,
            'successCount': 0,
            'scanPhones': [],
            'successModemCardInfos': [],
        }
    else:
        if not 'needCount' in shareStore:
            shareStore['needCount'] = needCount
        if not 'scanCount' in shareStore:
            shareStore['scanCount'] = 0
        if not 'successCount' in shareStore:
            shareStore['successCount'] = 0
        if not 'scanPhones' in shareStore:
            shareStore['scanPhones'] = []
        if not 'successModemCardInfos' in shareStore:
            shareStore['successModemCardInfos'] = []

    currNeedCount = needCount
    scanPhones = shareStore['scanPhones']
    scanTaskAmount = currNeedCount * scanTaskMultiple
    if scanTaskAmount > scanTaskMax:
        scanTaskAmount = scanTaskMax
    runTasks = []
    for modemCardInfo in modemCardInfos:
        phoneNumber = modemCardInfo['phone']
        if phoneNumber in scanPhones:
            continue
        else:
            scanPhones.append(phoneNumber)

        isTimeout, _ = _inputTimeout(
            confirmTimeoutSec,
            f'[_smsScan]: +{phoneNumber}'
            f' Go (pass <ENTER> or wait {confirmTimeoutSec} seconds to continue)'
        )
        if isTimeout:
            print()

        shareStore['scanCount'] += 1
        runTasks.append(
            _smsScanHandle(modemCardInfo, modemPoolTable, tgSignUpTool, shareStore)
        )

        if len(runTasks) == scanTaskAmount:
            await asyncio.gather(*runTasks)
            runTasks.clear()

            successCount = shareStore['successCount']
            if successCount < currNeedCount:
                currNeedCount = needCount - successCount
                scanTaskAmount = currNeedCount * scanTaskMultiple
                if scanTaskAmount > scanTaskMax:
                    scanTaskAmount = scanTaskMax
            else:
                break
    if len(runTasks) != 0:
        await asyncio.gather(*runTasks)
        runTasks.clear()

    return shareStore

async def _smsScanHandle(
        modemCardInfo: dict,
        modemPoolTable: ModemPoolTable,
        tgSignUpTool: TgSignUpTool,
        shareStore: dict):
    phoneNumber = modemCardInfo['phone']
    smsUrl = modemCardInfo['smsUrl']

    try:
        connectStete, client, _ = await tgSignUpTool.connect(phoneNumber)
        if client != None:
            await client.disconnect()
    except Exception as err:
        modemPoolTable.updateItem(
            modemCardInfo,
            state = 'TRIED',
            connectStateTxt = f'{err}'
        )
        raise err

    if connectStete != TgSignUpTool.connectStatus['SENDBYSMS']:
        if connectStete == TgSignUpTool.connectStatus['LOGINING']:
            print(f'[_smsScanHandle]: +{phoneNumber} 已登入，請清除掃描用的 session。')
            tgSignUpTool.mvSessionPath(phoneNumber, 'scanHasLogined')
        elif connectStete == TgSignUpTool.connectStatus['HASBANNED']:
            # The used phone number has been banned from Telegram and cannot be used any more.
            # Maybe check https://www.telegram.org/faq_spam
            print(f'[_smsScanHandle]: +{phoneNumber} has been banned.')
            modemPoolTable.updateItem(modemCardInfo, state = 'BANNED')
            tgSignUpTool.mvSessionPath(phoneNumber, 'scanRm')
        elif connectStete == TgSignUpTool.connectStatus['SENDBYAPP']:
            print(f'[_smsScanHandle]: +{phoneNumber} has been used.')
            modemPoolTable.updateItem(modemCardInfo, state = 'USED')
            tgSignUpTool.mvSessionPath(phoneNumber, 'scanErr')
        elif connectStete == TgSignUpTool.connectStatus['PHONENUMBERINVALID']:
            print(f'[_smsScanHandle]: +{phoneNumber} phone number is invalid.')
            modemPoolTable.updateItem(
                modemCardInfo,
                state = 'INVALID',
                connectStateTxt = connectStete
            )
            tgSignUpTool.mvSessionPath(phoneNumber, 'scanErr')
        else:
            print(
                f'[_smsScanHandle]: +{phoneNumber} skip.'
                f' (無法使用自動化登入，狀態： {connectStete})'
            )
            modemPoolTable.updateItem(
                modemCardInfo,
                state = 'TRIED',
                connectStateTxt = connectStete
            )

        return

    requestSmsState, verifiedCode = await tgSignUpTool.getSmsVerifiedCode(
        phoneNumber, smsUrl
    )
    if requestSmsState == TgSignUpTool.requestSmsStatus['OK']:
        shareStore['successCount'] += 1
        shareStore['successModemCardInfos'].append(modemCardInfo)
    else:
        modemPoolTable.updateItem(
            modemCardInfo,
            state = 'TRIED',
            connectStateTxt = requestSmsState
        )

async def _autoSignUpHandle(
        modemCardInfo: dict,
        modemPoolTable: ModemPoolTable,
        tgSignUpTool: TgSignUpTool,
        randomName: RandomName,
        groupPeer: str,
        shareStore: dict):
    phoneNumber = modemCardInfo['phone']
    smsUrl = modemCardInfo['smsUrl']

    signUpRunScanGetErrorMsg = 'signUp (scan) get error: '
    signUpGetErrorMsg = 'signUp get error: '

    try:
        connectStete, client, phoneCodeHash = await tgSignUpTool.connect(phoneNumber)
    except Exception as err:
        modemPoolTable.updateItem(
            modemCardInfo,
            state = 'TRIED',
            connectStateTxt = f'{signUpRunScanGetErrorMsg}{err}'
        )
        tgSignUpTool.mvSessionPath(phoneNumber, 'autoSignUpErr')
        raise err

    if connectStete != TgSignUpTool.connectStatus['SENDBYSMS']:
        # 資料有誤，需更新資料
        if connectStete == TgSignUpTool.connectStatus['LOGINING']:
            print(f'[_autoSignUpHandle]: +{phoneNumber} 已登入。')
            isSuccess = _autoSignUpHandle_callNiUser(
                modemCardInfo, modemPoolTable,
                tgSignUpTool,
                client, groupPeer,
                isHasLogined = True
            )
            if isSuccess:
                shareStore['successCount'] += 1
                tgSignUpTool.mvSessionPath(phoneNumber, '')
            else:
                tgSignUpTool.mvSessionPath(phoneNumber, 'whoami')
        elif connectStete == TgSignUpTool.connectStatus['HASBANNED']:
            print(f'[_autoSignUpHandle]: +{phoneNumber} has been banned.')
            modemPoolTable.updateItem(
                modemCardInfo,
                state = 'BANNED',
                connectStateTxt = f'{signUpRunScanGetErrorMsg}{connectStete}'
            )
            tgSignUpTool.mvSessionPath(phoneNumber, 'autoSignUpRm')
        else:
            print(
                f'[_autoSignUpHandle]: +{phoneNumber} skip.'
                f' (無法使用自動化登入，狀態： {connectStete})'
            )
            modemPoolTable.updateItem(
                modemCardInfo,
                state = 'INVALID',
                connectStateTxt = f'{signUpRunScanGetErrorMsg}{connectStete}'
            )
            tgSignUpTool.mvSessionPath(phoneNumber, 'autoSignUpErr')

        if client != None:
            await client.disconnect()
        return

    fullName, firstName, lastName = randomName.get()
    tryRemainingTime = 1
    while True:
        if shareStore['successCount'] >= shareStore['needCount']:
            break

        requestSmsState, verifiedCode = await tgSignUpTool.getSmsVerifiedCode(
            phoneNumber, smsUrl
        )
        if requestSmsState != TgSignUpTool.requestSmsStatus['OK']:
            modemPoolTable.updateItem(
                modemCardInfo,
                state = 'INVALID',
                connectStateTxt = f'{signUpRunScanGetErrorMsg}{requestSmsState}'
            )
            tgSignUpTool.mvSessionPath(phoneNumber, 'autoSignUpErr')
            break

        if shareStore['successCount'] >= shareStore['needCount']:
            break

        signUpStete = await tgSignUpTool.signUp(
            client, phoneNumber, verifiedCode, phoneCodeHash, firstName, lastName
        )

        if signUpStete == TgSignUpTool.signUpStatus['OK']:
            print(f'[_autoSignUpHandle]: +{phoneNumber} 註冊成功。')
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
                shareStore['successCount'] += 1
                tgSignUpTool.mvSessionPath(phoneNumber, '')
            else:
                tgSignUpTool.mvSessionPath(phoneNumber, 'whoami')
            break

        if tryRemainingTime > 0 and (
                    signUpStete == TgSignUpTool.signUpStatus['PHONECODEINVALID'] \
                    or signUpStete == TgSignUpTool.signUpStatus['PHONECODEEMPTY'] \
                    or signUpStete == TgSignUpTool.signUpStatus['PHONECODEEXPIRED']
                ):
            tryRemainingTime -= 1
            continue

        modemPoolTable.updateItem(
            modemCardInfo,
            state = 'INVALID',
            connectStateTxt = f'{signUpGetErrorMsg}{signUpStete}'
        )
        tgSignUpTool.mvSessionPath(phoneNumber, 'autoSignUpErr')
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
        print(f'[_autoSignUpHandle]: +{phoneNumber} 我是誰？')
        modemPoolTable.updateItem(
            modemCardInfo,
            state = 'INVALID',
            name = f'{fullName} (who am I ?)'
        )
        return False

    if callNiUserState == TgSignUpTool.callNiUserStatus['NOTPRESENT']:
        print(f'[_autoSignUpHandle]: +{phoneNumber} 未到場。')

    modemPoolTable.updateItem(modemCardInfo, state = 'OK', name = f'{niUserName}')
    return True

async def _checkOkHandle(
        modemCardInfo: dict,
        modemPoolTable: ModemPoolTable,
        tgSignUpTool: TgSignUpTool,
        shareStore: dict):
    phoneNumber = modemCardInfo['phone']

    checkOkGetErrorMsg = 'checkOk get error: '

    try:
        connectStete, client, _ = await tgSignUpTool.connect(phoneNumber)
    except Exception as err:
        # NOTE: 可能是環境錯誤，例如網路問題等等。
        raise err

    if connectStete == TgSignUpTool.connectStatus['LOGINING']:
        shareStore['activeCount'] += 1
        myName = await tgSignUpTool.getMyName(client)
        print(
            f'[_checkOkHandle]: +{phoneNumber} '
            f'Hi, I\'m {myName}.' if myName != None else 'say hi.'
        )
        await client.disconnect()
        return

    shareStore['exitedCount'] += 1
    if connectStete == TgSignUpTool.connectStatus['HASBANNED']:
        print(f'[_checkOkHandle]: +{phoneNumber} has been banned.')
        modemPoolTable.updateItem(
            modemCardInfo,
            state = 'OKBANNED',
            connectStateTxt = f'{connectStete}'
        )
        tgSignUpTool.mvSessionPath(phoneNumber, 'checkOkRm')
    else:
        print(f'[_checkOkHandle]: +{phoneNumber} 未登入. (狀態： {connectStete})')
        modemPoolTable.updateItem(
            modemCardInfo,
            state = 'INVALID',
            connectStateTxt = f'{checkOkGetErrorMsg}{connectStete}'
        )
        tgSignUpTool.mvSessionPath(phoneNumber, 'checkOkErr')

# https://stackoverflow.com/questions/15528939/python-3-timed-input
def _inputTimeout(timeout: int, promptTxt: str) -> typing.Tuple[bool, str]:
    sys.stdout.write(promptTxt)
    sys.stdout.flush()
    ready, _, _ = select.select([sys.stdin], [], [], timeout)
    # expect stdin to be line-buffered
    inputTxt = sys.stdin.readline().rstrip('\n') if ready else ''
    return (not ready, inputTxt)

def _inputYesOrNo(inputTxt: str) -> str:
    if inputTxt == 'Yes' or inputTxt == 'yes' or inputTxt == 'Y' or inputTxt == 'y':
        return 'yes'
    elif inputTxt == 'No' or inputTxt == 'no' or inputTxt == 'N' or inputTxt == 'n':
        return 'no'
    else:
        return inputTxt


def run(args: list, _dirpy: str, _dirname: str):
    asyncio.run(asyncRun(args, _dirpy, _dirname))

