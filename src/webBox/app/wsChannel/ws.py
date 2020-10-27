#!/usr/bin/env python3


import typing
import asyncio
import webBox.app._wsChannel.niUsersStatus as niUsersStatus


def subscribe(pageId: str, prop: typing.Any = None) -> dict:
    if prop == 'latestStatus':
        asyncio.create_task(niUsersStatus.subscribe(pageId))
        return {'result': True}

