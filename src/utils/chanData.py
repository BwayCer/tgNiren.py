#!/usr/bin/env python3


import typing
import os
import sys
import rejson
import utils.json


_dirname = os.path.dirname(os.path.abspath(sys.argv[0]))
_env = utils.json.loadYml(_dirname + '/env.yml')

_redisKey = 'tgNiren'
_chanDataFilePath = _dirname + '/data.redis.json'

_rjdb = rejson.Client(
    host = _env['redisService']['host'],
    port = _env['redisService']['port'],
    decode_responses = True
)
_ysUpdate = False


class ChanData():
    def __init__(self):
        if _rjdb.jsonget(_redisKey, rejson.Path.rootPath()) == None:
            if os.path.exists(_chanDataFilePath):
                data = utils.json.load(_chanDataFilePath)
            else:
                data = {}

            _rjdb.jsonset(_redisKey, rejson.Path.rootPath(), data)

    # 想參考 https://github.com/SPSCommerce/redlock-py
    # 但執行 `dlm.lock(_redisKey, timeout)` 時會拋出以下錯誤
    #   ERROR:root:Error unlocking resource tg_niren
    #     in server Redis<ConnectionPool<Connection<host=localhost,port=6379,db=0>>>
    #   redis.exceptions.ResponseError: Error running script
    #     (call to f_4e92fdc63815b3a0a2dd1c1df3694de73607c88d): @user_script:2:
    #     WRONGTYPE Operation against a key holding the wrong kind of value
    def dFakeLockSet(memberPath: str = '.', ysStore: bool = False, maxTimes: int = -1):
        def realDecorator(fn):
            def _getSafe(memberPath: str) -> typing.Any:
                try:
                    data = _rjdb.jsonget(_redisKey, rejson.Path(memberPath))
                except:
                    data = None
                return data

            def newFn(*args) -> bool:
                times = 0
                while True:
                    originData = _getSafe(memberPath)
                    newData = fn(*args)
                    # Python 的比較其內容，與 JS 比較其物件指針不同
                    if originData == _getSafe(memberPath):
                        _rjdb.jsonset(_redisKey, rejson.Path(memberPath), newData)
                        _ysUpdate = True
                        if ysStore:
                            _ysUpdate = False
                            rootData = _rjdb.jsonget(_redisKey, rejson.Path.rootPath())
                            utils.json.dump(rootData, _chanDataFilePath)
                        return True

                    if maxTimes != -1:
                        times += 1
                        if times >= maxTimes:
                            return False
            return newFn
        return realDecorator

    def store(self):
        if _ysUpdate:
            rootData = _rjdb.jsonget(_redisKey, rejson.Path.rootPath())
            utils.json.dump(rootData, _chanDataFilePath)

    def opt(self, method: str, memberPath: str, *args) -> typing.Any:
        methodFn = getattr(_rjdb, method)
        if len(args) == 0:
            return methodFn(_redisKey, rejson.Path(memberPath))
        else:
            value = args[0]
            result = methodFn(_redisKey, rejson.Path(memberPath), value)
            _ysUpdate = True
            return result

    def set(self, memberPath: str, value: typing.Any) -> bool:
        ysSet = self.opt('jsonset', memberPath, value)
        return ysSet

    def get(self, memberPath: str) -> typing.Any:
        return self.opt('jsonget', memberPath)

    def getSafe(self, memberPath: str) -> typing.Any:
        try:
            data = self.opt('jsonget', memberPath)
        except:
            data = None
        return data

    def dele(self, memberPath: str) -> bool:
        result = self.opt('jsondel', memberPath)
        ysDelete = True if result == 1 else False
        return ysDelete

