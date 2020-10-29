#!/usr/bin/env python3


import typing
import asyncio
import utils.novice as novice
import webBox.serverMix as serverMix
import webBox.app.utils as appUtils


__all__ = ['subscribe', 'updateStatus']


_subscriber = []
_prevStatus = {'allCount': 0, 'usableCount': 0}


async def subscribe(pageId: str):
    if novice.indexOf(_subscriber, pageId) == -1:
        _subscriber.append(pageId)

        if len(_subscriber) == 1:
            task = asyncio.create_task(_latestStatus())
            novice.logNeedle.push(
                f'{task.get_name()} _wsChannel/niUsersStatus: task start'
            )

    await _send(pageId, _getNiUsersStatusTxt(_prevStatus))

async def updateStatus(allCount: int = 0, usableCount: int = 0):
    if allCount + usableCount == 0:
        return

    allCount = _prevStatus['allCount'] + allCount
    allCount = _prevStatus['allCount'] = allCount if allCount > 0 else 0

    usableCount = _prevStatus['usableCount'] + usableCount
    _prevStatus['usableCount'] = 0 if usableCount < 0 else \
        usableCount if usableCount <= allCount else allCount

    await _sendAll()


async def _latestStatus():
    taskName = asyncio.current_task().get_name()

    while True:
        novice.logNeedle.push(f'{taskName} _wsChannel/niUsersStatus again')
        niUsersStatusInfo = await appUtils.getNiUsersStatusInfo()
        allCount = niUsersStatusInfo['allCount']
        usableCount = niUsersStatusInfo['usableCount']
        isChange = _prevStatus['allCount'] != allCount \
            or _prevStatus['usableCount'] != usableCount

        novice.logNeedle.push(
            f'{taskName} _wsChannel/niUsersStatus isChange:'
            f' {isChange} {allCount} {usableCount}'
        )
        if isChange:
            _prevStatus['allCount'] = allCount
            _prevStatus['usableCount'] = usableCount

        await _sendAll(isChange)

        novice.logNeedle.push(
            f'{taskName} _wsChannel/niUsersStatus len(subscriber): {len(_subscriber)}'
        )
        if len(_subscriber) == 0:
            novice.logNeedle.push(
                f'{taskName} _wsChannel/niUsersStatus: task end'
            )
            break
        else:
            novice.logNeedle.push(f'{taskName} _wsChannel/niUsersStatus sleep 60')
            await asyncio.sleep(60)
            novice.logNeedle.push(f'{taskName} _wsChannel/niUsersStatus getUp')


async def _send(pageId: str, niUsersStatusTxt: str):
    try:
        innerSession = serverMix.innerSession.get(pageId)
        latestStatus = innerSession['latestStatus'] \
            if innerSession != None and 'latestStatus' in innerSession else None
        await serverMix.wsHouse.send(
            pageId,
            fnResult = {
                'name': 'niUsersStatus.latestStatus',
                'result': {
                    'niUsersStatus': niUsersStatusTxt,
                    'latestStatus': latestStatus,
                },
            }
        )
    except Exception as err:
        novice.logNeedle.push(
            'from {} pageId: {}, innerSession: {} Failed {}'.format(
                'latestStatus_send',
                pageId,
                innerSession,
                novice.sysTracebackException()
            )
        )

async def _sendAll(isChange: bool = True):
    niUsersStatusTxt = _getNiUsersStatusTxt(_prevStatus)
    for pageId in _subscriber:
        if not serverMix.wsHouse.hasRoom(pageId):
            _subscriber.remove(pageId)
            break

        if isChange:
            await _send(pageId, niUsersStatusTxt)


def _getNiUsersStatusTxt(info: dict) -> str:
    return '仿用戶可用比： {}/{}'.format(info['usableCount'], info['allCount'])

