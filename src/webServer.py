#!/usr/bin/env python3


import os
import quart
import utils.chanData
import utils.novice as novice
import webBox.serverMix as serverMix
import webBox.controller.ws


def main():
    # 初始化狀態
    novice.logNeedle.push('服務器啟動 ...')
    chanData = utils.chanData.ChanData()
    if chanData.getSafe('.niUsers') == None:
        chanData.data['niUsers'] = {
            'cemetery': [],
            'bandInfos': [],
            'bandList': [],
            'lockList': [],
        }
    chanData.data['niUsers']['lockList'].clear()


    app = quart.Quart(
        __name__,
        static_url_path = '/',
        static_folder = './webBox/static',
        template_folder = './webBox/pages'
    )

    @app.before_serving
    async def beforeServing():
        serverMix.enableTool('InnerSession', 'WsHouse')

        router = serverMix.Router(app, 'webBox.controller')
        router.add('GET', '/', 'home.get_home')
        router.add('GET', '/allRespond', 'home.get_allRespond')

        webBox.controller.ws.init('webBox/app/wsChannel')
        router.websocket('/ws', 'ws.entry')

    app.run(host = '0.0.0.0', port = 5000, debug=True)


if __name__ == '__main__':
    main()
    os._exit(0)

