#!/usr/bin/env python3

import sys
import os
import re

_origArgs = sys.argv
_pyTool = {
    'adTool.sendAdPhoto': 'adTool/sendAdPhoto',
    'adTool.sendForward': 'adTool/sendForward',
    'adTool.getParticipants': 'adTool/getParticipants',
    'adTool.tuckUserIntoChannel': 'adTool/tuckUserIntoChannel',
    'tgPing.interactiveLogin.simple': 'tgPing/simple-interactiveLogin',
    'tgPing.sendMessage.simple': 'tgPing/simple-sendMessage',
    'tgPing.sendForward.simple': 'tgPing/simple-sendForward',
}

if len(_origArgs) == 1:
    raise Exception('[tool]: Not found command.')
elif _origArgs[1] in '--router':
    for name in _pyTool:
        print('  => {}: {}'.format(name, _pyTool[name]))
elif _origArgs[1] in _pyTool:
    import importlib
    import utils.novice as novice
    try:
        importlib.import_module(
            'toolBox.' + _pyTool[_origArgs[1]].replace('/', '.')
        ).run(
            [_origArgs[0], *_origArgs[2:]],
            os.path.dirname(novice.py_dirname + '/toolBox/' + _pyTool[_origArgs[1]]),
            novice.py_dirname
        )
    except Exception as err:
        logNeedle = novice.LogNeedle()
        logNeedle.pushException()
        raise err
else:
    raise Exception('[tool]: Not found "' + _origArgs[1] + '" command.')

