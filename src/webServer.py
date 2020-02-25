#!/usr/bin/env python3


import os
import quart
import webBox.serverMix as serverMix


def main() -> None:
    app = quart.Quart(
        __name__,
        static_url_path = '/',
        static_folder = './webBox/static',
        template_folder = './webBox/pages'
    )

    serverMix.enableTool('InnerSession')

    router = serverMix.Router(app, 'webBox.controller')
    router.add('GET', '/', 'home.get')
    router.add('POST', '/', 'home.post')
    router.add('POST', '/api/latestStatus', 'home.api_latestStatus__Po')

    app.run(host = '0.0.0.0', port = 5000, debug=True)


if __name__ == '__main__':
    main()
    os._exit(0)

