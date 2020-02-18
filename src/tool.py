#!/usr/bin/env python3

import sys
import os
import re

_dirname = os.path.dirname(os.path.abspath(sys.argv[0]))
_origArgs = sys.argv
_pyTool = {
    'login.interactiveLogin.simple': 'toolBox/login/simple-interactiveLogin',
    'adTool.sendAdPhoto': 'toolBox/adTool/sendAdPhoto',
    'adTool.getParticipants': 'toolBox/adTool/getParticipants',
    'adTool.tuckUserIntoChannel': 'toolBox/adTool/tuckUserIntoChannel',
}

if len(_origArgs) == 1:
    raise Exception('[tool]: Not found command.')
elif _origArgs[1] in '--router':
    for name in _pyTool:
        print('  => {}: {}'.format(name, _pyTool[name]))
elif _origArgs[1] in _pyTool:
    import importlib
    import utils.chanData
    try:
        importlib.import_module(
            _pyTool[_origArgs[1]].replace('/', '.')
        ).run(
            [_origArgs[0], *_origArgs[2:]],
            os.path.dirname(_dirname + '/' + _pyTool[_origArgs[1]]),
            _dirname
        )
    except Exception as err:
        logNeedle = utils.chanData.LogNeedle()
        logNeedle.pushException()
        raise err
else:
    raise Exception('[tool]: Not found "' + _origArgs[1] + '" command.')

