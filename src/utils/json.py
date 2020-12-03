#!/usr/bin/env python3


import json
import yaml


__all__ = ['load', 'loadYml', 'dump']


def load(filePath: str):
    with open(filePath, 'r', encoding = 'utf-8') as fs:
        dataTxt = fs.read()
    data = json.loads(dataTxt)
    return data

# DEPRECATION `yaml.load()`
# https://github.com/yaml/pyyaml/wiki/PyYAML-yaml.load(input)-Deprecation
def loadYml(filePath: str):
    with open(filePath, 'r', encoding = 'utf-8') as fs:
        data = yaml.load(fs,  Loader=yaml.SafeLoader)
    return data

def dump(data, filePath: str = None, indent: int = 2):
    dataTxt = json.dumps(data, indent = indent, ensure_ascii = False)
    if filePath != None:
        with open(filePath, 'w', encoding = 'utf-8') as fs:
            fs.write(dataTxt)
    return dataTxt

