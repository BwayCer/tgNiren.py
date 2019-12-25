#!/usr/bin/env python3


import typing
import traceback
import sys
import atexit
import time
import datetime


# 異常退出時執行
#   @dOnExit
#   def onExit():
#       print('異常退出')
def dOnExit(fn) -> None:
    atexit.register(fn)

def dTryCatch(fn) -> typing.Callable[..., typing.Any]:
    def wrapTryCatch(*args) -> typing.Any:
        try:
            return fn(*args)
        except Exception:
            print(sysTracebackException(ysIsWrapTryCatch = True))
    return wrapTryCatch

def sysTracebackException(
        ysHasTimestamp: bool = False,
        ysIsWrapTryCatch: bool = False) -> str:
    exc_type, exc_obj, exc_tb = sys.exc_info()
    callStackList = traceback.extract_tb(exc_tb)

    txt = '{} Error: {}'.format(exc_type, exc_obj)

    if ysHasTimestamp:
        txt += '\n  Timestamp: {}'.format(dateStringify(dateNow()))

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


def indexOf(target: typing.Union[str, list], index, *args) -> int:
    try:
        return target.index(index, *args)
    except ValueError:
        return -1


def dateTimestamp(dt: datetime.datetime) -> int:
    # 不管是 UTC 或者本地時間所返回的毫秒數都是相對本地時間的毫秒數
    # datetime.datetime.now(datetime.timezone.utc).timestamp()
    # datetime.datetime.now().timestamp()
    localDtstamp = int(dt.timestamp() * 1000)
    utcDtstamp = localDtstamp + (time.timezone * 1000)
    return utcDtstamp

def dateStringify(dt: datetime.datetime) -> str:
    dtMs = dateTimestamp(dt)
    dtstamp = dtMs / 1000
    return datetime.datetime.fromtimestamp(dtstamp).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
    # return datetime.datetime.now().replace(tzinfo=datetime.timezone.utc).isoformat()

def dateNow() -> datetime.datetime:
    return datetime.datetime.now()

def dateNowTimestamp() -> int:
    return dateTimestamp(dateNow())

