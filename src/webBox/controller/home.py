#!/usr/bin/env python3


import typing
import quart
import utils.novice as novice
import webBox.serverMix as serverMix
from tgkream.tgTool import tgTodoFunc
import webBox.app.api.adTool.sendAdPhoto as api_adTool_sendAdPhoto


async def get() -> quart.Response:
    if not _wwwAuth.verifyAuth(quart.request.authorization):
        return _wwwAuth.getLoginResponse()

    response = quart.Response(await quart.render_template('index.html'))
    pageId = quart.request.cookies.get('pageId')
    if not serverMix.innerSession.hasPageId(pageId):
        pageId = serverMix.innerSession.open(_getDefaultPageSession())
        response.set_cookie('pageId', pageId)
    return response

async def post():
    if not _wwwAuth.verifyAuth(quart.request.authorization):
        return _apiError(401, '未登入。')

    pageId = quart.request.cookies.get('pageId')
    pageInnerSession = serverMix.innerSession.get(pageId)

    if pageInnerSession == None:
        return _apiError(404, '頁面識別碼過期。')

    try:
        # if data == None & to use "data" -> TypeError
        data = await quart.request.get_json()
        method = data['method']
    except Exception as err:
        return _apiError(
            400,
            '請求參數值錯誤。 ({}: {})'.format(type(err), err)
        )

    try:
        methodFunc = None
        if method == 'paperSlipAction':
            methodFunc = _apiPaperSlipAction

        if methodFunc != None:
            return await methodFunc(pageInnerSession, data)
        else:
            return _apiError(404, '請求方法不存在。')
    except Exception as err:
        return _apiError(400, '{}: {}'.format(type(err), err))

async def api_latestStatus__Po():
    if not _wwwAuth.verifyAuth(quart.request.authorization):
        return _controller._apiError(401, '未登入。')

    pageId = quart.request.cookies.get('pageId')
    pageInnerSession = serverMix.innerSession.get(pageId)

    if pageInnerSession == None:
        return _controller._apiError(404, '頁面識別碼過期。')

    niUsersStatusInfo = tgTodoFunc.getNiUsersStatusInfo()
    return quart.jsonify({
        'niUsersStatus': '仿用戶可用比： {}/{} ({})'.format(
            niUsersStatusInfo['lockCount'],
            niUsersStatusInfo['allCount'],
            '工具可用' if niUsersStatusInfo['allCount'] - niUsersStatusInfo['lockCount'] > 3 else '工具不可用'
        ),
        'latestStatus': pageInnerSession['latestStatus']
    })


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


def _apiError(statusCode, message):
    return quart.jsonify({'message': message}), statusCode

async def _apiPaperSlipAction(pageInnerSession, data):
    niUsersStatusInfo = tgTodoFunc.getNiUsersStatusInfo()
    if pageInnerSession['runing']:
        return quart.jsonify({
            'message': '工具執行中。'
        }), 200
    elif niUsersStatusInfo['allCount'] - niUsersStatusInfo['lockCount'] > 0:
        try:
            # if data == None & to use "data" -> TypeError
            newData = {
                'forwardPeerList': data['forwardPeerList'],
                'mainGroup': data['mainGroup'],
                'messageId': data['messageId'],
            }
        except Exception as err:
            return _apiError(400, '請求參數值錯誤。 ({}: {})'.format(type(err), err))

        asyncio.ensure_future(api_adTool_sendAdPhoto.asyncRun(pageInnerSession, newData, novice.py_dirname))
        return quart.jsonify({
            'message': '請求已接收。'
        }), 200
    else:
        return quart.jsonify({
            'message': '工具目前無法使用。',
        }), 200

