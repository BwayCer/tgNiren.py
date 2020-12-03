#!/usr/bin/env python3


import pdb
import typing
import os
import sys
import random
import time
import datetime
import re
import asyncio
import select
import requests
import utils.json
import telethon as telethon
import utils.novice as novice


TelegramClient = telethon.TelegramClient

_envModemPool = novice.py_env['modemPool']
_nameListFilePath = novice.py_dirname + '/' + _envModemPool['nameListFilePath']

_asyncRun_autoLogin_tasksAmountMax = 1
_voipTable_gPickVoipInfo_inputTimeoutSec = 0.1 # 3
_tgSmsCode_get_inputTimeoutSec = 0.1 # 7


def _run_txtToJson(voipTxtFilePath: str):
    voipTableFilePath = voipTxtFilePath + '.json'
    with open(voipTxtFilePath, 'r', encoding = 'utf-8') as fs:
        voipInfos = []
        regeCindyVoipTxt = r'^(\d+)\|([0-9a-fA-F]+)\n$'
        lines = fs.readlines()
        for line in lines:
            matchTgCode = re.search(regeCindyVoipTxt, line)

            if not matchTgCode:
                raise Exception(f'不符合預期的格式 ({line})')

            number = matchTgCode.group(1)
            token = matchTgCode.group(2)
            voipInfos.append({
                'state': 'never',
                # 加拿大的虛擬號碼
                'phone': '1' + number,
                'token': token,
                'name': '',
            })

        utils.json.dump(voipInfos, voipTableFilePath)

async def _asyncRun_autoLogin(
        voipTableFilePath: str,
        groupPeer: str,
        middleName: str):
    apiId = novice.py_env['apiId']
    nameList = utils.json.loadYml(_nameListFilePath)
    tgSigninTool = _TgSigninTool(
        apiId,
        novice.py_env['apiHash'],
        sessionPrefix = 'cindy/telethon-' + apiId + '-',
        groupCode = groupPeer,
        randomName = _RandomName(middleName, nameList)
    )
    voipTable = _VoipTable(voipTableFilePath)
    tgSmsCode = _tgSmsCode(novice.py_env['cindy']['registerUrl'])

    runLoginTasks = []
    for voipInfo in voipTable.gPickVoipInfo():
        runLoginTasks.append(
            _autoLoginHandle(voipInfo, tgSigninTool, voipTable, tgSmsCode)
        )

        if len(runLoginTasks) == _asyncRun_autoLogin_tasksAmountMax:
            await asyncio.gather(*runLoginTasks)
            runLoginTasks.clear()

    if len(runLoginTasks) != 0:
        await asyncio.gather(*runLoginTasks)

async def _run_checkOk(voipTableFilePath: str):
    apiId = novice.py_env['apiId']
    nameList = utils.json.loadYml(_nameListFilePath)
    voipTable = _VoipTable(voipTableFilePath)

    sessionPrefix = 'cindy/telethon-' + apiId + '-';

    for voipInfo in voipTable.gPickOkVoipInfo():
        # if not idx < 30: break
        phoneNumber = voipInfo['phone']
        token = voipInfo['token']

        # result = tgSigninTool.connect(phoneNumber)
        sessionFilePathPart = sessionPrefix + phoneNumber
        sessionFilePath = sessionFilePathPart + '.session'
        if not os.path.exists(sessionFilePath):
            print(f'找不到 "{sessionFilePath}" 文件。')

        client = TelegramClient(sessionFilePathPart, apiId, novice.py_env['apiHash'])

        try:
            await client.connect()
        except Exception as err:
            print(f'+{phoneNumber}')
            print('from client.connect() failed {} Error: {}', type(err), err)
            pdb.set_trace()
            continue

        if await client.is_user_authorized():
            print('[run]: 驗證通過')
            continue

        try:
            result = await client.send_code_request(phoneNumber)
        except telethon.errors.PhoneNumberBannedError as err:
            print('[run]: The used phone number has been banned')
            voipTable.setItemState(voipInfo, 'BANNED')
            continue
        except Exception as err:
            print(f'from client.connect() failed {type(err)} Error: {err}')
            continue

        sentCodeType = type(result.type)
        if sentCodeType == telethon.types.auth.SentCodeTypeSms:
            print('send by sms')
        elif sentCodeType == telethon.types.auth.SentCodeTypeApp:
            print('send by app')
        elif sentCodeType == telethon.types.auth.SentCodeTypeFlashCall:
            print('send by flash call')
        elif sentCodeType == telethon.types.auth.SentCodeTypeCall:
            print('send by call')


class _TimeoutExpired(Exception):
    pass

class _RandomName():
    def __init__(self, lastPrefix: str, nameList: dict):
        self._lastPrefix = lastPrefix
        self._nameList = nameList
        self._nameListLength = len(nameList)

    def getOne(self) -> str:
        return self._nameList[random.randrange(0, self._nameListLength)]

    def get(self) -> typing.Tuple[str, str, str]:
        firstName = self.getOne()
        lastName = self._lastPrefix + self.getOne()
        return (firstName + ' ' + lastName, firstName, lastName)

class _VoipTable():
    def __init__(self, filePath: str):
        if not os.path.exists(filePath):
            raise Exception(f'Not found {filePath} (voipTableFile)')

        self.filePath = filePath
        self.data = utils.json.load(filePath)

    state = {
        'NEVER': 'never',
        'RUNNING': 'running',
        'BANNED': 'Banned',
        'TRIED': 'Tried',
        'OK': 'ok',
    }

    def gPickVoipInfo(self) -> dict:
        inputTimeoutSec = _voipTable_gPickVoipInfo_inputTimeoutSec

        for voipInfo in self.data:
            state = voipInfo['state']
            phoneNumber = voipInfo['phone']

            tmpMsg = '[_VoipTable.gPickVoipInfo]: +{}.'.format(phoneNumber)
            if state == self.state['RUNNING']:
                tmpMsg += ' continue'
            elif state == self.state['NEVER']:
                self.setItemState(voipInfo, 'RUNNING')
            else:
                tmpMsg += ' skip. (state: {})'.format(state)
                print(tmpMsg)
                continue
            tmpMsg += f' Go (pass <ENTER> or wait {inputTimeoutSec} seconds to continue)'
            try:
                _inputTimeout(inputTimeoutSec, tmpMsg)
            except _TimeoutExpired:
                print()

            yield voipInfo

    def gPickOkVoipInfo(self) -> dict:
        inputTimeoutSec = _voipTable_gPickVoipInfo_inputTimeoutSec

        for voipInfo in self.data:
            state = voipInfo['state']
            phoneNumber = voipInfo['phone']

            tmpMsg = '[_VoipTable.gPickVoipInfo]: +{}.'.format(phoneNumber)
            if state != self.state['OK']:
                tmpMsg += ' skip. (state: {})'.format(state)
                print(tmpMsg)
                continue
            tmpMsg += f' Go (pass <ENTER> or wait {inputTimeoutSec} seconds to continue)'
            try:
                _inputTimeout(inputTimeoutSec, tmpMsg)
            except _TimeoutExpired:
                print()

            yield voipInfo

    def store(self) -> None:
        utils.json.dump(self.data, self.filePath)

    def setItemState(self, voipInfo: dict, state: str) -> None:
        voipInfo['state'] = self.state[state]
        self.store()

    def setFinalNmae(self, voipInfo: dict, name: str) -> None:
        voipInfo['state'] = self.state['OK']
        voipInfo['name'] = name
        self.store()

class _TgSigninTool():
    def __init__(self,
            apiId: str,
            apiHash: str,
            sessionPrefix: str,
            groupCode: str,
            randomName: _RandomName):
        self.apiId = apiId
        self.apiHash = apiHash
        self.sessionPrefix = sessionPrefix
        self._groupCode = groupCode
        self._randomName = randomName
        self._client = None

        sessionDirPath = os.path.dirname(sessionPrefix)
        if not os.path.exists(sessionDirPath):
            os.makedirs(sessionDirPath)

    connectStete = {
        'LOGINING': 'logining',
        'SENDBYSMS': 'send by sms',
        'SENDBYAPP': 'send by app',
        'SENDBYCALL': 'send by call',
        'HASBANNED': 'has banned',
        'APIIDINVALID': 'API ID 無效',
        'PHONENUMBERFLOOD': '您請求代碼的次數過多',
        'PHONENUMBERINVALID': '電話號碼是無效的',
        'PHONEPASSWORDFLOOD': '您嘗試登錄太多次了',
        # 'OTHER': 'any message',
    }

    async def connect(self, phoneNumber: str) -> typing.Union[None, str]:
        sessionFilePathPart = self.sessionPrefix + phoneNumber
        # self._client = TelegramClient(sessionFilePathPart, self.apiId, self.apiHash)
        self._client = TelegramClient(
            sessionFilePathPart,
            self.apiId,
            self.apiHash,
            device_model = 'iPhone SE (2nd gen)',
            system_version = 'Android 9p (28)'
        )
        client = self._client

        try:
            await client.connect()
        except Exception as err:
            print('from client.connect() failed {} Error: {}', type(err), err)
            pdb.set_trace()

        if await client.is_user_authorized():
            return self.connectStete['LOGINING']

        print(f'[_TgSigninTool.connect]: send +{phoneNumber} request.')
        try:
            result = await client.send_code_request(phoneNumber, force_sms = True)
        except telethon.errors.ApiIdInvalidError as err:
            return self.connectStete['APIIDINVALID']
        except telethon.errors.PhoneNumberBannedError as err:
            return self.connectStete['HASBANNED']
        except telethon.errors.PhoneNumberFloodError as err:
            return self.connectStete['PhoneNumberFlood']
        except telethon.errors.PhoneNumberInvalidError as err:
            return self.connectStete['PhoneNumberInvalid']
        except telethon.errors.PhonePasswordFloodError as err:
            return self.connectStete['PHONEPASSWORDFLOOD']
        except Exception as err:
            return f'from client.connect() failed {type(err)} Error: {err}'

        sentCodeType = type(result.type)
        if sentCodeType == telethon.types.auth.SentCodeTypeSms:
            return self.connectStete['SENDBYSMS']
        elif sentCodeType == telethon.types.auth.SentCodeTypeApp:
            return self.connectStete['SENDBYAPP']
        elif sentCodeType == telethon.types.auth.SentCodeTypeFlashCall:
            return self.connectStete['SENDBYCALL']
        elif sentCodeType == telethon.types.auth.SentCodeTypeCall:
            return self.connectStete['SENDBYCALL']

        print('[_TgSigninTool.connect]: {} != {}. ({})'.format(
            sentCodeType,
            telethon.types.auth.SentCodeTypeSms,
            result
        ))
        return None

    async def sayHi(self, txt: str = '') -> telethon.types.Updates:
        await self._client(telethon.functions.channels.JoinChannelRequest(
            channel = self._groupCode
        ))
        await self._client(telethon.functions.messages.SendMessageRequest(
            peer = self._groupCode,
            message = 'Hi{}'.format(f', {txt}' if txt != '' else ''),
            random_id = random.randrange(1000000, 9999999)
        ))

    async def signUp(self, phoneNumber: str, verifiedCode: str) -> None:
        client = self._client
        try:
            await client.sign_in(phoneNumber, verifiedCode)
        except telethon.errors.PhoneNumberUnoccupiedError as err:
            _, firstName, lastName = self._randomName.get()
            await client.sign_up(verifiedCode, firstName, lastName)
            print()
            # 成功的話會出現下列訊息 :
            # By signing up for Telegram, you agree not to:
            #
            # - Use our service to send spam or scam users.
            # - Promote violence on publicly viewable Telegram bots, groups or channels.
            # - Post pornographic content on publicly viewable Telegram bots, groups or channels.
            #
            # We reserve the right to update these Terms of Service later.

    async def getMyName(self) -> typing.Union[str, None]:
        meInfo = await self._client.get_me()
        if meInfo == None:
            return meInfo
        return f'{meInfo.first_name} {meInfo.last_name}'

class _tgSmsCode():
    def __init__(self, registerUrl: str):
        self.registerUrl = registerUrl

    state = {
        'OK': 'ok',
        'SKIP': 'skip',
    }

    _requestState = {
        'ERROR': -1,
        'HTTPSTATUSCODEERROR': 0,
        'NOTHASMESSAGE': 1,
        'OTHERMESSAGE': 2,
        'SUCCESS': 3,
    }

    async def get(self, token: str, phoneNumber: str = '---') -> typing.Tuple[str, str]:
        inputTimeoutSec = _tgSmsCode_get_inputTimeoutSec

        waitOnceTimeSec = 30
        waitTimeSec = waitOnceTimeSec
        startTimeSec = datetime.datetime.now().timestamp()

        while True:
            sys.stdout.write('.')
            sys.stdout.flush()

            nextTimeSec = 4
            requestState, msg = self._requestSms(self.registerUrl + token)
            if requestState == self._requestState['ERROR']:
                print(' (err: {})'.format(msg))
                nextTimeSec = 12
            elif requestState == self._requestState['HTTPSTATUSCODEERROR']:
                print(' (err: http status code: {})'.format(msg))
                nextTimeSec = 12
            elif requestState == self._requestState['OTHERMESSAGE']:
                print(' (other message: {})'.format(msg))

                try:
                    verifiedCodeInput = _inputTimeout(
                        inputTimeoutSec,
                        f'[_tgSmsCode.get]: +{phoneNumber} input verified code'
                        ' (pass <ENTER> continue waiting or input "skip" to skip'
                        ' (default, or wait {inputTimeoutSec} seconds to skip)): '
                    )
                except _TimeoutExpired:
                    print()
                    verifiedCodeInput = 'skip'


                if verifiedCodeInput == 'skip':
                    return (self.state['SKIP'], '')
                elif verifiedCodeInput != '':
                    return (self.state['OK'], verifiedCodeInput)
                else:
                    nextTimeSec = 4
            elif requestState == self._requestState['SUCCESS']:
                print('\n[_tgSmsCode.get]: message: {}'.format(msg))
                return (self.state['OK'], msg)

            if datetime.datetime.now().timestamp() - startTimeSec > waitTimeSec:
                waitTimeMinute = waitTimeSec / 60
                tmpMsg =  '\n[_tgSmsCode.get]:' \
                         f' +{phoneNumber} 已超過 {waitTimeMinute} 分鐘'

                tmpMsg +=  '，是否還要繼續' \
                          f' (默認跳過，或者等待 {inputTimeoutSec} 後自動跳過) ? [Y/N]: '
                try:
                    continueInput = _inputYesOrNo(_inputTimeout(inputTimeoutSec, tmpMsg))
                except _TimeoutExpired:
                    print()
                    continueInput = 'no'

                if continueInput == 'yes':
                    startTimeSec = datetime.datetime.now().timestamp()
                    waitTimeSec += waitOnceTimeSec
                else:
                    return (self.state['SKIP'], '')
            else:
                await asyncio.sleep(nextTimeSec)

    def _requestSms(self, url: str) -> typing.Tuple[int, str]:
        try:
            response = requests.get(url, timeout = 12)

            if response.status_code == 200:
                smsData = response.json()
                smsMsg = smsData['message']

                if len(smsData['data']) > 0:
                    print('\n[_tgSmsCode._requestSms]: data: {}'.format(smsData))

                stateMethod = 'NOTHASMESSAGE'
                if smsMsg != 'No has message':
                    stateMethod = 'OTHERMESSAGE'
                    verifiedCode = self._getVerifiedCode(smsMsg)
                    if verifiedCode != None:
                        return (self._requestState['SUCCESS'], verifiedCode)

                return (self._requestState[stateMethod], smsMsg)
            else:
                return (self._requestState['HTTPSTATUSCODEERROR'], response.status_code)
        except Exception as err:
            return (self._requestState['ERROR'], type(err))

    def _getVerifiedCode(self, smsMsg: str) -> typing.Union[str, None]:
        matchTgCode = re.search(self._getVerifiedCode_regeTgCode, smsMsg)

        if not matchTgCode:
            return None

        tgCode = matchTgCode.group(1)
        return tgCode

    _getVerifiedCode_regeTgCode = r'^(?:t|T)elegram code (\d{5})$'

async def _autoLoginHandle(
        voipInfo: dict,
        tgSigninTool: _TgSigninTool,
        voipTable: _VoipTable,
        tgSmsCode: _tgSmsCode):
    phoneNumber = voipInfo['phone']
    token = voipInfo['token']

    result = await tgSigninTool.connect(phoneNumber)

    if result == _TgSigninTool.connectStete['LOGINING']:
        print(f'[run]: +{phoneNumber} 驗證通過')
        return
    if result == _TgSigninTool.connectStete['HASBANNED']:
        # The used phone number has been banned from Telegram and cannot be used any more.
        # Maybe check https://www.telegram.org/faq_spam
        print(f'[run]: +{phoneNumber} The used phone number has been banned')
        voipTable.setItemState(voipInfo, 'BANNED')
        return
    elif result != _TgSigninTool.connectStete['SENDBYSMS']:
        print(f'[run]: +{phoneNumber} skip. (無法使用自動化登入) ({result})')
        print(f'[run]: +{phoneNumber} # {result} != {_TgSigninTool.connectStete["SENDBYSMS"]}.')
        voipTable.setItemState(voipInfo, 'TRIED')
        return

    tgSmsCodeState, verifiedCode = await tgSmsCode.get(token, phoneNumber)
    if tgSmsCodeState != _tgSmsCode.state['OK']:
        voipTable.setItemState(voipInfo, 'TRIED')
        return

    voipTable.setItemState(voipInfo, 'OK')
    print(f'[run]: +{phoneNumber} 可以使用')
    await tgSigninTool.signUp(phoneNumber, verifiedCode)

    myName = await tgSigninTool.getMyName()
    if myName != None:
        print(f'My name is {myName} and phone is {phoneNumber}.')
        await tgSigninTool.sayHi(f'I\'m {myName}')
        voipTable.setFinalNmae(voipInfo, myName)
    else:
        print('[run]: Error(找不到我)')
        pdb.set_trace()

def _inputYesOrNo(inputTxt: str) -> str:
    if inputTxt == 'Yes' or inputTxt == 'yes' or inputTxt == 'Y' or inputTxt == 'y':
        return 'yes'
    elif inputTxt == 'No' or inputTxt == 'no' or inputTxt == 'N' or inputTxt == 'n':
        return 'no'
    else:
        return inputTxt

# https://stackoverflow.com/questions/15528939/python-3-timed-input
def _inputTimeout(timeout: int, promptTxt: str) -> str:
    sys.stdout.write(promptTxt)
    sys.stdout.flush()
    ready, _, _ = select.select([sys.stdin], [], [], timeout)
    if ready:
        # expect stdin to be line-buffered
        return sys.stdin.readline().rstrip('\n')
    raise _TimeoutExpired


def run(args: list, _dirpy: str, _dirname: str):
    txtToJsonUsageTxt = 'txtToJson <voipTxtFilePath>'
    autoLoginUsageTxt = 'autoLogin <voipTableFilePath> <groupPeer> <middleName>'
    checkOkUsageTxt = 'checkOk <voipTableFilePath>'

    argsLength = len(args)
    if argsLength > 1:
        method = args[1]
        if method == 'txtToJson':
            if argsLength < 3:
                raise ValueError(f'Usage: {txtToJsonUsageTxt}')

            voipTxtFilePath = args[2]
            _run_txtToJson(voipTxtFilePath)
            return
        elif method == 'autoLogin':
            if argsLength < 5:
                raise ValueError(f'Usage: {autoLoginUsageTxt}')

            voipTableFilePath = args[2]
            groupPeer = args[3]
            middleName = args[4]
            asyncio.run(
                _asyncRun_autoLogin(voipTableFilePath, groupPeer, middleName)
            )
            return
        elif method == 'checkOk':
            if argsLength < 3:
                raise ValueError(f'Usage: {checkOkUsageTxt}')

            voipTableFilePath = args[2]
            asyncio.run(_run_checkOk(voipTableFilePath))
            return

    raise ValueError(
        f'Usage: {txtToJsonUsageTxt}\n'
        f'       {autoLoginUsageTxt}\n'
        f'       {checkOkUsageTxt}'
    )

