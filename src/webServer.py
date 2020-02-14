#!/usr/bin/env python3


import os
# https://pgjones.gitlab.io/quart/source/quart.static.html
import quart


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
            return response

def main() -> None:
    app = quart.Quart(
        __name__,
        static_url_path = '/',
        static_folder = './webpages',
        template_folder = './webpages'
    )

    _controller.home(app)

    app.run(host = '0.0.0.0', port = 5000, debug=True)


if __name__ == '__main__':
    main()
    os._exit(0)

