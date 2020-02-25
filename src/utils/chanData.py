#!/usr/bin/env python3


import typing
import os
import sys
import utils.novice as novice
import utils.json


_logFilePath = novice.py_dirname + '/' + novice.py_env['logFilePath']
_chanDataFilePath = novice.py_dirname + '/' + novice.py_env['chanDataFilePath']

_data = None


class ChanData():
    def __init__(self):
        global _data

        if _data == None:
            if os.path.exists(_chanDataFilePath):
                _data = utils.json.load(_chanDataFilePath)
            else:
                _data = {}

        self.data = _data

    def store(self):
        utils.json.dump(self.data, _chanDataFilePath)

    def getSafe(self, memberPath: str) -> typing.Any:
        try:
            data = self.data
            memberList = memberPath.split('.')
            for idx in range(1, len(memberList)):
                member = memberList[idx]
                if type(data) == list:
                    member = int(member)
                if member in data:
                    data = data[member]
                else:
                    data = None
                    break
        except:
            data = None
        return data


class LogNeedle():
    def __init__(self): pass

    def push(self, text: str) -> None:
        logTxt = '-~@~- {}\n{}\n\n'.format(
            novice.dateStringify(novice.dateNow()),
            text
        )
        with open(_logFilePath, 'a', encoding = 'utf-8') as fs:
            fs.write(logTxt)

    def pushException(self) -> bool:
        logTxt = novice.sysTracebackException()
        self.push(logTxt)

