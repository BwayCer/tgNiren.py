#!/usr/bin/env python3
import sys
import os
import re
_dirname = os.path.dirname(os.path.abspath(sys.argv[0]))
_origArgs= sys.argv
_pyTool = {}
if len(_origArgs) == 1:
    raise Exception('[otherTool]: Not found command')
elif _origArgs[1] in '--router':
    for name in _pyTool:
        print('  {}: {}'.format(name, _pyTool[name]))
elif _origArgs[1] in _pyTool:
    import importlib
    importlib.import_module(
        _pyTool[_origArgs[1]].replace('/', '.')
    ).run(
        os.path.dirname(_dirname + '/' + _pyTool[_origArgs[1]]),
        [_origArgs[0], *_origArgs[2:]]
    )
else:
    raise Exception('[otherTool]: Not found "' + _origArgs[1] + '" command')
