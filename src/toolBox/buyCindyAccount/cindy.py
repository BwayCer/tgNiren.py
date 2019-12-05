#!/usr/bin/env python3


import pdb
import typing
import os
import sys
import random
import time
import re
import json
import requests
import utils.json
import telethon.sync as telethon
import datetime


TelegramClient = telethon.TelegramClient


def run(args: list, _dirpy: str, _dirname: str):
    method = args[1]
    if method == 'txtToJson':
        voipTxtFilePath = args[2]
        run_txtToJson(voipTxtFilePath)
    elif method == 'autoLogin':
        voipTableFilePath = args[2]
        groupPeer = args[3]
        middleName = args[4]
        _env = utils.json.loadYml(_dirname + '/env.yml')
        run_autoLogin(_dirpy, _env, voipTableFilePath, groupPeer, middleName)

def run_txtToJson(voipTxtFilePath: str):
    voipTableFilePath = voipTxtFilePath + '.json'
    with open(voipTxtFilePath, 'r', encoding = 'utf-8') as fs:
        voipInfos = []
        regeCindyVoipTxt = r'^(\d+)\|([0-9a-f]+)\n$'
        lines = fs.readlines()
        for line in lines:
            matchTgCode = re.search(regeCindyVoipTxt, line)

            if not matchTgCode:
                raise Exception('不符合預期的格式 ({})'.format(line))

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

def run_autoLogin(
        _dirpy: str,
        _env: dict,
        voipTableFilePath: str,
        groupPeer: str,
        middleName: str):
    voipTable = _VoipTable(voipTableFilePath)
    nameList = utils.json.loadYml(_dirpy + '/nameList.yml')
    tgSigninTool = _TgSigninTool(
        apiId = _env['apiId'],
        apiHash = _env['apiHash'],
        sessionPrefix = 'newTgSession/telethon-',
        groupCode = groupPeer,
        randomName = _RandomName(middleName, nameList)
    )

    for voipInfo in voipTable.gPickVoipInfo():
        # if not idx < 30: break
        phoneNumber = voipInfo['phone']
        token = voipInfo['token']

        result = tgSigninTool.connect(phoneNumber)

        if result == _TgSigninTool.connectStete['LOGINING']:
            print('[run]: skip. (電話號碼已存在並且驗證通過)')
            voipTable.setItemState(voipInfo, 'OK')
            continue
        if result == _TgSigninTool.connectStete['HASBANNED']:
            # The used phone number has been banned from Telegram and cannot be used any more.
            # Maybe check https://www.telegram.org/faq_spam
            print('[run]: skip. (The used phone number has been banned)')
            continue
        elif result != _TgSigninTool.connectStete['SENDBYSMS']:
            print('[run]: skip. (無法使用自動化登入) ({})'.format(result))
            print('[run]: {} != {}.'.format(result, _TgSigninTool.connectStete['SENDBYSMS']))
            continue

        tgSmsCodeState, verifiedCode = _tgSmsCode.get(token)
        tgSigninTool.signUp(phoneNumber, verifiedCode)

        myName = tgSigninTool.getMyName()
        if not myName:
            print('[run]: Error(找不到我)')
            pdb.set_trace()

        tgSigninTool.joinGroup()
        voipTable.setFinalNmae(voipInfo, myName)

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
    state = {
        'NEVER': 'never',
        'RUNNING': 'running',
        'UPBANNED': 'upBanned',
        'INBANNED': 'inBanned',
        'OK': 'ok',
    }

    def __init__(self, filePath: str):
        if not os.path.exists(filePath):
            raise Exception('Not Found {} (voipTableFile)'.format(filePath))

        self.filePath = filePath
        self.data = utils.json.load(filePath)

    def gPickVoipInfo(self) -> dict:
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
            # TODO 增加默認 3 秒後自動繼續的功能
            tmpMsg += ' Go (pass <ENTER> to continue)'
            sys.stdout.write(tmpMsg)
            sys.stdout.flush()
            time.sleep(3)
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

    def connect(self, phoneNumber: str) -> typing.Union[None, str]:
        sessionFilePathPart = self.sessionPrefix + phoneNumber
        self._client = TelegramClient(sessionFilePathPart, self.apiId, self.apiHash)
        client = self._client

        self._client.connect()
        if client.is_user_authorized():
            return self.connectStete['LOGINING']

        try:
            result = self._client.send_code_request(phoneNumber)
        except telethon.errors.PhoneNumberBannedError as err:
            return self.connectStete['HASBANNED']

        print('[_TgSigninTool.connect]: send +{} request.'.format(phoneNumber))
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

    connectStete = {
        'HASBANNED': 'has banned',
        'LOGINING': 'logining',
        'SENDBYSMS': 'send by sms',
        'SENDBYAPP': 'send by app',
        'SENDBYCALL': 'send by call',
    }

    def joinGroup(self) -> telethon.types.Updates:
        return self._client(telethon.functions.channels.JoinChannelRequest(
            channel = self._groupCode
        ))

    def signUp(self, phoneNumber: str, verifiedCode: str) -> None:
        client = self._client
        try:
            client.sign_in(phoneNumber, verifiedCode)
        except telethon.errors.PhoneNumberUnoccupiedError as err:
            _, firstName, lastName = self._randomName.get()
            client.sign_up(verifiedCode, firstName, lastName)
            # 成功的話會出現下列訊息 :
            # By signing up for Telegram, you agree not to:
            #
            # - Use our service to send spam or scam users.
            # - Promote violence on publicly viewable Telegram bots, groups or channels.
            # - Post pornographic content on publicly viewable Telegram bots, groups or channels.
            #
            # We reserve the right to update these Terms of Service later.

    def getMyName(self) -> typing.Union[str, None]:
        meInfo = self._client.get_me()
        if not meInfo:
            return meInfo
        return meInfo.first_name + ' ' + meInfo.last_name

class _tgSmsCode():
    state = {
        'OK': 'ok',
    }

    _requestState = {
        'ERROR': -1,
        'HTTPSTATUSCODEERROR': 0,
        'NOTHASMESSAGE': 1,
        'OTHERMESSAGE': 2,
        'SUCCESS': 3,
    }

    def get(token: str) -> typing.Tuple[typing.Union[None, str], str]:
        registerUrl = 'http://47.105.90.14/napi/view?token='
        waitOnceTimeSec = 180
        waitTimeSec = waitOnceTimeSec
        startTimeSec = datetime.datetime.now().timestamp()

        while True:
            sys.stdout.write('.')
            sys.stdout.flush()

            nextTimeSec = 4
            requestState, msg = _tgSmsCode._requestSms(registerUrl + token)
            if requestState == _tgSmsCode._requestState['ERROR']:
                print(' (err: {})'.format(msg))
                nextTimeSec = 12
            elif requestState == _tgSmsCode._requestState['HTTPSTATUSCODEERROR']:
                print(' (err: http status code: {})'.format(msg))
                nextTimeSec = 12
            elif requestState == _tgSmsCode._requestState['OTHERMESSAGE']:
                print(' (other message: {})'.format(msg))
                pdb.set_trace()
            elif requestState == _tgSmsCode._requestState['SUCCESS']:
                print('\n[_tgSmsCode.get]: message: {}'.format(msg))
                return (_tgSmsCode.state['OK'], msg)

            if datetime.datetime.now().timestamp() - startTimeSec > waitTimeSec:
                # TODO 增加對話互動
                # 已超過 {} 分鐘，是否還要繼續 ( Yes: y; No: n )
                print('\n[_tgSmsCode.get]: 已超過 {} 分鐘'.format(waitTimeSec / 60))
                waitTimeSec += waitOnceTimeSec
            else:
                time.sleep(nextTimeSec)

    def _requestSms(url: str) -> typing.Tuple[int, str]:
        nextTimeSec = 4
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
                    verifiedCode = _tgSmsCode._getVerifiedCode(smsMsg)
                    if verifiedCode != None:
                        return (_tgSmsCode._requestState['SUCCESS'], verifiedCode)

                return (_tgSmsCode._requestState[stateMethod], smsMsg)
            else:
                return (_tgSmsCode._requestState['HTTPSTATUSCODEERROR'], response.status_code)
        except Exception as err:
            return (_tgSmsCode._requestState['ERROR'], type(err))

    def _getVerifiedCode(smsMsg: str) -> typing.Union[str, None]:
        matchTgCode = re.search(_tgSmsCode._getVerifiedCode_regeTgCode, smsMsg)

        if not matchTgCode:
            return None

        tgCode = matchTgCode.group(1)
        return tgCode

    _getVerifiedCode_regeTgCode = r'^telegram code (\d{5})$'


