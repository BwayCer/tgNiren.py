#!/usr/bin/env python3


import traceback
import os
import sys
import datetime
import utils.json


py_dirname = os.path.dirname(os.path.abspath(sys.argv[0]))

py_envDirname = py_dirname + '/env'
if os.path.exists(py_envDirname + '/env.yml'):
    py_env = utils.json.loadYml(py_envDirname + '/env.yml')
    _logFilePath = py_dirname + '/' + py_env['logFilePath']
else:
    raise Exception(f'找不到 {py_envDirname}/env.yml 環境文件。')


class LogNeedle():
    def __init__(self): pass

    def push(self, text: str) -> None:
        print(text)
        logTxt = '-~@~- {}\n{}\n\n'.format(
            dateUtcStringify(dateUtcNow()),
            text
        )
        with open(_logFilePath, 'a', encoding = 'utf-8') as fs:
            fs.write(logTxt)

    def pushException(self) -> bool:
        logTxt = sysTracebackException()
        self.push(logTxt)

logNeedle = LogNeedle()


def sysTracebackException(
        ysHasTimestamp: bool = False,
        ysIsWrapTryCatch: bool = False) -> str:
    exc_type, exc_obj, exc_tb = sys.exc_info()
    callStackList = traceback.extract_tb(exc_tb)

    txt = '{} Error: {}'.format(exc_type, exc_obj)

    if ysHasTimestamp:
        txt += '\n  Timestamp: {}'.format(dateUtcStringify(dateUtcNow()))

    txt += '\n  Traceback:'
    # idx == 0 是指向此 wrapTryCatch 函式
    idxStart = 1 if ysIsWrapTryCatch else 0
    for idx in range(idxStart, len(callStackList)):
        callStack = callStackList[idx]
        txt += '\n    File {}, line {}, in {}'.format(
            callStack[0],
            callStack[1],
            callStack[2]
        )

    return txt


def dateUtcNow() -> datetime.datetime:
    return datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)

def dateUtcStringify(dtUtc: datetime.datetime) -> str:
    return dtUtc.strftime('%Y-%m-%dT%H:%M:%S.%fZ')

