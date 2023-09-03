#!/usr/bin/env python3


import os
import asyncio
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
        router.add('GET', '/person', 'person.get')

        webBox.controller.ws.init('webBox/app/wsChannel')
        router.websocket('/ws', 'ws.entry')

    app.run(host = '0.0.0.0', port = 5000, debug = False)

sleepTask = None
async def toSleep(time: int):
    global sleepTask
    # sleepTask = asyncio.create_task(asyncio.sleep(time))
    print(asyncio.current_task().get_name())
    if sleepTask == None:
        sleepTask = asyncio.current_task()

    try:
        await asyncio.sleep(time)
    except asyncio.CancelledError:
        print(f'client close connect 2.')
        # raise # 會拋出 asyncio.CancelledError
    finally:
        print(f'server close connect 2.')

async def test2():
    try:
        while True:
            print(9, asyncio.current_task().get_name())
            print(1)
            await toSleep(5)
            print(2)
            await asyncio.sleep(10)
            print(3)
    except asyncio.CancelledError:
        print(f'client close connect.')
        pass
    finally:
        print(f'server close connect.')

async def test():
    task = asyncio.create_task(test2())
    await asyncio.sleep(18)
    print('test')
    sleepTask.cancel()


if __name__ == '__main__':
    # asyncio.run(test())
    main()
    os._exit(0)

    # async def factorial(name, number):
        # f = 1
        # for i in range(2, number + 1):
            # print(f"Task {name}: Compute factorial({i})...")
            # await asyncio.sleep(1)
            # f *= i
        # print(f"Task {name}: factorial({number}) = {f}")

    # await asyncio.gather(
        # factorial('A1', 20),
        # factorial('B1', 20),
        # factorial('C1', 20),
        # factorial('D1', 20),
        # factorial('E1', 20),
        # factorial('F1', 20),
        # factorial('G1', 20),
        # factorial('H1', 20),
        # factorial('I1', 20),
        # factorial('J1', 20),
        # factorial('K1', 20),
        # factorial('L1', 20),
        # factorial('M1', 20),
        # factorial('N1', 20),
        # factorial('O1', 20),
        # factorial('P1', 20),
        # factorial('R1', 20),
        # factorial('S1', 20),
        # factorial('T1', 20),
        # factorial('U1', 20),
        # factorial('V1', 20),
        # factorial('X1', 20),
        # factorial('W1', 20),
        # factorial('Y1', 20),
        # factorial('Z1', 20),
    # )

