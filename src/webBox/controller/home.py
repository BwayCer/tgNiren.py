#!/usr/bin/env python3


import quart
import utils.novice as novice
import webBox.serverMix as serverMix


async def get() -> quart.Response:
    if not _wwwAuth.verifyAuth(quart.request.authorization):
        return _wwwAuth.getLoginResponse()

    response = quart.Response(await quart.render_template('index.html'))
    pageId = quart.request.cookies.get('pageId')
    if not serverMix.innerSession.hasPageId(pageId):
        pageId = serverMix.innerSession.open(_getDefaultPageSession())
        response.set_cookie('pageId', pageId)
    return response


class _wwwAuth():
    def getLoginResponse() -> quart.Response:
        return quart.Response(
            'Could not verify your access level for that URL.\n'
            'You have to login with proper credentials',
            401,
            {'WWW-Authenticate': 'Basic realm="Login Required"'}
        )

    def verifyAuth(auth: dict) -> bool:
        return auth and auth.username == 'mars' and auth.password == 'nobody'

def _getDefaultPageSession() -> dict:
    return {
        'runing': False,
        'latestStatus': None
    }

