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


class ChanData():
    def __init__(self):
        if _rjdb.jsonget(_redisKey, rejson.Path.rootPath()) == None:
            if os.path.exists(_chanDataFilePath):
                data = utils.json.load(_chanDataFilePath)
            else:
                data = {}

            _rjdb.jsonset(_redisKey, rejson.Path.rootPath(), data)

    def store(self) -> bool:
        data = self.get('.')
        utils.json.dump(data, _chanDataFilePath)
        return True

    def opt(self, method: str, memberPath: str, *args) -> typing.Any:
        methodFn = getattr(_rjdb, method)
        if len(args) == 0:
            return methodFn(_redisKey, rejson.Path(memberPath))
        else:
            value = args[0]
            return methodFn(_redisKey, rejson.Path(memberPath), value)

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

