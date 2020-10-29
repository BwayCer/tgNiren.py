#!/usr/bin/env python3


import typing
import asyncio
import utils.novice as novice
import webBox.app._wsChannel.niUsersStatus as niUsersStatus


def subscribe(pageId: str, wsId: str, prop: typing.Any = None) -> dict:
    if prop == 'latestStatus':
        novice.logNeedle.push(f'subscribe latestStatus: {pageId}')
        asyncio.create_task(niUsersStatus.subscribe(pageId))
        return True

