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

# 異步說明
# # 暫停時間
#   `time.sleep(secN)` 應該是使執行程式睡眠 結果上看仍然是同步
#   `asyncio.sleep(secN)` 使用此方法才能有異步效果
# # 執行第一個異步函式的函式
#   asyncio.run(firstCoroutine())
#   or
#   def dAsyncRun(fnCoroutine):
#       def newFn(*args):
#           loop = asyncio.get_event_loop()
#           result = loop.run_until_complete(fnCoroutine())
#           loop.close()
#           return result
#       return newFn
#
#   # 可執行異步函式 但僅接收同步的回傳值 並且不會等待異步完成
#   def dAsyncRun(fnCoroutine):
#       try:
#           result = fnCoroutine().send(None)
#           print('result: ', result)
#       except StopIteration as err:
#           print('StopIteration: ', err)
#           return err.value
# # 範例
# import asyncio
# import random
#
# async def B(idCode):
#     sleepSec = random.randrange(1, 6)
#     print('Waiting {} Seconds for {} ...'.format(idCode, sleepSec))
#     await asyncio.sleep(sleepSec)
#     if sleepSec % 2 == 0:
#         raise KeyError('The {} id not found'.format(idCode))
#     print('Hi {}.'.format(idCode))
#     return 'Hi {}.'.format(idCode)
#
# async def A():
#     try:
#         # finisheds = await asyncio.gather(B('AA'), B('AB'), B('AC'),
#         #         return_exceptions = True)
#         finisheds = await asyncio.gather(*[B('AA'), B('AB'), B('AC')],
#                 return_exceptions = True)
#         for finished in finisheds:
#             if isinstance(finished, Exception):
#                 print('err:', finished)
#
#         # finished, _ = await asyncio.wait([B('AA'), B('AB')])
#         # print('-A-')
#     except KeyError as err:
#         print('-B-')
#         print('nn KeyError: ', err)
#     except Exception as err:
#         print('hi', err)
#         sys.exit(1)
#
# asyncio.run(A())


# import os
# import sys
# import types
# from contextlib import contextmanager
#
#
# _originStdout = sys.stdout
# _originStderr = sys.stderr
#
# def echo(txt: str):
#     _originStdout.write(txt)
#     _originStdout.flush()
#
# def echoErr(txt: str):
#     _originStderr.write(txt)
#     _originStderr.flush()
#
# def pecho(txt: str):
#     _originStdout.write('echo>> {}'.format(txt))
#     _originStdout.flush()
#
# def pechoErr(txt: str):
#     _originStderr.write('echo>> {}'.format(txt))
#     _originStderr.flush()
#
#
# @contextmanager
# def pipeDevnull(p = -1):
#     writeDevnull = open(os.devnull, 'w')
#     originStdout = sys.stdout
#     originStderr = sys.stderr
#     if p == -1 or p == 1:
#         sys.stdout = writeDevnull
#     if p == -1 or p == 2:
#         sys.stderr = writeDevnull
#     yield
#     if p == -1 or p == 1:
#         sys.stdout = originStdout
#     if p == -1 or p == 2:
#         sys.stderr = originStderr
#
# @contextmanager
# def tryCatch(printErrMsg = True, exit1OnError = False, onError = None):
#     try:
#         yield
#     except Exception as err:
#         errType = err.__class__.__name__
#         errMsg = err.args[0]
#         if printErrMsg == True:
#             print('error>> <{}> {}'.format(errType, errMsg))
#         if isinstance(onError, types.FunctionType):
#             onError(errType, errMsg)
#         if exit1OnError == True:
#             raise err
#             os._exit(1)


# def _handlePick(data: typing.Any, memberPath: str = '', *args) -> typing.Any:
#     ysHasDataPart = len(args) > 0
#     dataPart = None
#     if ysHasDataPart:
#         dataPart = args[0]
#
#     pickData = data
#     regeInt = r'^\d+$'
#     ysTypeList = False
#
#     memberNameList = memberPath.split('.')
#     memberNameListLenth = len(memberNameList)
#     memberNamelastIdx = memberNameListLenth - 1
#     for idx in range(memberNameListLenth):
#         memberName = memberNameList[idx]
#         ysTypeList = type(pickData) == list
#
#         if not memberName in pickData:
#             ysNotMember = True
#             matches = re.match(regeInt, memberName)
#             if matches:
#                 index = int(memberName)
#                 if ysTypeList and index < len(pickData):
#                     ysNotMember = False
#
#             if ysNotMember:
#                 raise KeyError(
#                         'not found "{}" member of "{}".'.format(memberName, memberPath))
#
#         if ysHasDataPart and idx == memberNamelastIdx:
#             pickData[index if ysTypeList else memberName] = dataPart
#
#         pickData = pickData[index if ysTypeList else memberName]
#
#     return pickData
#
# def readNiUsersData(memberPath: str = '') -> typing.Any:
#     data = utils.json.load(_niUsersFilePath)
#     return _handlePick(data, memberPath)
#
# def storeNiUsersData(dataPart: typing.Any, memberPath: str = '') -> typing.Any:
#     data = utils.json.load(_niUsersFilePath)
#     pickData = _handlePick(data, memberPath, dataPart)
#     utils.json.dump(data, _niUsersFilePath)
#     return pickData

