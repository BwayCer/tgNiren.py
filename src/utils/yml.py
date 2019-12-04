#!/usr/bin/env python3


import yaml


__all__ = ['load', 'dump']


# DEPRECATION `yaml.load()`
# https://github.com/yaml/pyyaml/wiki/PyYAML-yaml.load(input)-Deprecation
def load(filePath: str):
    with open(filePath, 'r') as fs:
        data = yaml.load(fs,  Loader=yaml.SafeLoader)
    return data

def dump(data):
    return yaml.dump(data)

