#!/usr/bin/env python3


import typing
import os
import random
# https://pgjones.gitlab.io/quart/source/quart.static.html
import quart
import utils.novice
from tgkream.tgTool import tgTodoFunc


class _fakeSession():
    def __init__(self):
        self._data = {}
        self._ynClose = True

    # TODO 看能不能改成計時器執行
    def expiredCheck(self) -> None:
        sessionData = self._data
        nowTimeMs = utils.novice.dateNowTimestamp()
        for key in list(sessionData):
            pageData = sessionData[key]
            if pageData['expiryTimestamp'] < nowTimeMs:
                del sessionData[key]

    def open(self, pageId: str, pageSession: dict) -> None:
        self.expiredCheck()
        expiryDate = utils.novice.dateNowAfter(hours = 4)
        self._data[pageId] = {
            'expiryTimestamp': utils.novice.dateTimestamp(expiryDate),
            'data': pageSession,
        }

    def get(self, pageId: str) -> typing.Union[None, dict]:
        sessionData = self._data
        if pageId in sessionData:
            pageData = sessionData[pageId]
            expiryDate = utils.novice.dateNowAfter(hours = 4)
            pageData['expiryTimestamp'] = utils.novice.dateTimestamp(expiryDate)
            return pageData['data']

        return None

_session = _fakeSession()

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

# get, post, head, put, patch, delete
class _controller():
    def home(app) -> None:
        def _getDefaultPageSession() -> dict:
            return {
                'runing': False,
                'latestStatus': None
            }

        @app.route('/')
        async def _home() -> quart.Response:
            if not _wwwAuth.verifyAuth(quart.request.authorization):
                return _wwwAuth.getLoginResponse()

            response = quart.Response(await quart.render_template('index.html'))
            pageId = quart.request.cookies.get('pageId')
            if pageId == None or _session.get(pageId) == None:
                pageId = hex(random.randrange(16777216, 268435455))[2:]
                _session.open(pageId, _getDefaultPageSession())
                response.set_cookie('pageId', pageId)
            return response

    def _apiError(statusCode, message):
        return quart.jsonify({'message': message}), statusCode

    def api_latestStatus__Po(app) -> None:
        @app.route('/api/latestStatus' , methods=['POST'])
        async def _api_latestStatus__Po():
            if not _wwwAuth.verifyAuth(quart.request.authorization):
                return _controller._apiError(401, '未登入。')

            pageId = quart.request.cookies.get('pageId')
            pageSession = _session.get(pageId)

            if pageSession == None:
                return _controller._apiError(404, '頁面識別碼過期。')

            niUsersStatusInfo = tgTodoFunc.getNiUsersStatusInfo()
            return quart.jsonify({
                'niUsersStatus': '仿用戶可用比： {}/{} ({})'.format(
                    niUsersStatusInfo['lockCount'],
                    niUsersStatusInfo['allCount'],
                    '工具可用' if niUsersStatusInfo['allCount'] - niUsersStatusInfo['lockCount'] > 3 else '工具不可用'
                ),
                'latestStatus': pageSession['latestStatus']
            })

def main() -> None:
    app = quart.Quart(
        __name__,
        static_url_path = '/',
        static_folder = './webpages',
        template_folder = './webpages'
    )

    _controller.home(app)
    _controller.api_latestStatus__Po(app)

    app.run(host = '0.0.0.0', port = 5000, debug=True)


if __name__ == '__main__':
    main()
    os._exit(0)

