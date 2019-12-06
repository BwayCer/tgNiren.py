#!/usr/bin/env python3

import sys
import os
import re

_dirname = os.path.dirname(os.path.abspath(sys.argv[0]))
_origArgs = sys.argv
_pyTool = {}

if len(_origArgs) == 1:
    raise Exception('[tool]: Not found command.')
elif _origArgs[1] in '--router':
    for name in _pyTool:
        print('  => {}: {}'.format(name, _pyTool[name]))
elif _origArgs[1] in _pyTool:
    import importlib
    importlib.import_module(
        _pyTool[_origArgs[1]].replace('/', '.')
    ).run(
        [_origArgs[0], *_origArgs[2:]],
        os.path.dirname(_dirname + '/' + _pyTool[_origArgs[1]]),
        _dirname
    )
else:
    raise Exception('[tool]: Not found "' + _origArgs[1] + '" command.')

