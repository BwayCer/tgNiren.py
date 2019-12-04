#!/usr/bin/env python3


import os
import sys
import utils.yml
from tgkream.tgTool import TgLoginTool


_dirname = os.path.dirname(os.path.abspath(sys.argv[0]))
_env = utils.yml.load(_dirname + '/env.yml')


def main():
    tgTool = TgLoginTool(
        _env['apiId'],
        _env['apiHash'],
        _dirname + '/_tgSession/telethon-'
    )
    for phoneNumber in _env['allPhoneNumber']:
        tgTool.login(phoneNumber)


if __name__ == '__main__':
    main()
    os._exit(0)

