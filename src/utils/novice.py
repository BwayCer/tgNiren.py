#!/usr/bin/env python3


import typing
import atexit
import time
import datetime


# 異常退出時執行
#   @dOnExit
#   def onExit():
#       print('異常退出')
def dOnExit(fn) -> None:
    atexit.register(fn)


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

