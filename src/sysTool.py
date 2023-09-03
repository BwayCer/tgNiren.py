#!/usr/bin/env python3


import telethon
import platform


print(
    f'device_model:   {platform.uname().machine}\n'
    f'system_version: {platform.uname().release}\n'
    f'app_version:    {telethon.version.__version__}'
)

