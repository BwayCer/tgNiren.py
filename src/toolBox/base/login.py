#!/usr/bin/env python3


import sys
import os
import select
import telethon.sync as telethon
    # from telethon.sync import TelegramClient as TelegramClientSync
    # from telethon import TelegramClient
    # print(TelegramClient is TelegramClientSync) # True
    # 取得的類型相同，但在測試登入時的回傳值確有同步、異步的差別
import utils.json


TelegramClient = telethon.TelegramClient


def run(args: list, _dirpy: str, _dirname: str):
    sessionDirPath = args[1]
    phoneNumbers = args[2:]

    _env = utils.json.loadYml(_dirname + '/env.yml')

    if not os.path.exists(sessionDirPath):
        os.makedirs(sessionDirPath)

    timeoutSec = 3
    for phoneNumber in phoneNumbers:
        promptTxt = '--- The +{} phone Go (pass <ENTER> or wait {} seconds to continue)'

        try:
            inputTimeout(timeoutSec, promptTxt.format(phoneNumber, timeoutSec))
        except TimeoutExpired:
            print('')

        client = TelegramClient(
            sessionDirPath + '/telethon-' + phoneNumber,
            _env['apiId'],
            _env['apiHash']
        )
        client.connect()

        if not client.is_user_authorized():
            # 文字或數字類型 Telethon 都接受，不過建議為文字
            # 可忽略 "+" 符號
            # if phoneNumber == '+8869xxx', input '8869xxx' (str)
            try:
                client.send_code_request(phoneNumber)
            except telethon.errors.rpcerrorlist.PhoneNumberInvalidError as err:
                print('The phone number +{} is invalid '.format(phoneNumber))
                continue
            except telethon.errors.rpcerrorlist.PhoneNumberBannedError as err:
                errMsg = 'The used phone number +{}'
                errMsg += ' has been banned from Telegram and cannot be used anymore.'
                errMsg += ' Maybe check https://www.telegram.org/faq_spam'
                print(errMsg.format(phoneNumber))
                continue

            while True:
                try:
                    verifiedCode = input(
                        'login {}, Enter the code: '.format(phoneNumber)
                    )
                    client.sign_in(phoneNumber, verifiedCode)
                    break
                except telethon.errors.PhoneCodeInvalidError as err:
                    print('The phone code entered was invalid')
                    continue

        meInfo = client.get_me()
        print('>>> Hi {}({}): id: {}, username: {}'.format(
            meInfo.first_name + ' ' + meInfo.last_name,
            phoneNumber,
            meInfo.id,
            meInfo.username,
        ))

# https://stackoverflow.com/questions/15528939/python-3-timed-input
class TimeoutExpired(Exception):
    pass

def inputTimeout(timeout: int, promptTxt: str) -> str:
    sys.stdout.write(promptTxt)
    sys.stdout.flush()
    ready, _, _ = select.select([sys.stdin], [], [], timeout)
    if ready:
        # expect stdin to be line-buffered
        return sys.stdin.readline().rstrip('\n')
    raise TimeoutExpired

