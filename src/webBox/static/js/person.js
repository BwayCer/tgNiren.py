'use strict';


(async _ => {
    const ws = new WebSocket('ws://' + document.domain + ':' + location.port + '/ws');
    let wsId = '';
    await (function connectWs(ws) {
        ws.onopen = function () {
            ws.send('pin')
        };

        return new Promise(function (resolve, reject) {
            let isSendHandshake = false;
            let timerId = setTimeout(function () {
                ws.close();
                alert('連線超時 請試試重整網頁 (F5)');
                reject(Error('WebSocket connection timeout.'));
            }, 10000);
            ws.onmessage = function (evt) {
                let receiveDataTxt = evt.data;

                if (isSendHandshake) {
                    let receiveData;
                    try {
                        receiveData = JSON.parse(receiveDataTxt);
                    } catch (err) {
                        return;
                    }
                    if (receiveData === null || typeof receiveData !== 'object') {
                        return;
                    }
                    if (receiveData.stateCode === 401 && 'wsId' in receiveData) {
                        wsId = receiveData.wsId;
                        ws.send(`{"wsId": "${wsId}"}`);
                        return;
                    }
                    if (receiveData.stateCode === 200 && receiveData.wsId === wsId) {
                        clearTimeout(timerId);
                        resolve('ok');
                        return;
                    }
                } else if (receiveDataTxt === 'pon') {
                    isSendHandshake = true;
                    ws.send('handshake')
                }
            };
        });
    })(ws);

    ws.onclose = function (evt) {
        alert('失去連線 請試試重整網頁 (F5)');
    };
    ws.onerror = function (evt) {
        alert('失去連線 請試試重整網頁 (F5)');
    };

    function getRandomId() {
        return parseInt(Math.random().toString().substr(-7));
    }

    let wsMethodBox = {};
    ws.onmessage = function (evt) {
        let receiveDatas;
        let receiveDatasTxt = evt.data;
        console.log(receiveDatasTxt);

        try {
            receiveDatas = JSON.parse(receiveDatasTxt);
        } catch (err) {
            console.error(err)
        }

        if (receiveDatas === null
            || typeof receiveDatas !== 'object'
            || receiveDatas.wsId !== wsId) {
            console.error('丟棄資料： ' + receiveDatasTxt)
        }

        if ('rtns' in receiveDatas && receiveDatas.rtns.constructor === Array) {
            let rtns = receiveDatas.rtns
            let key, item, type;
            for (key in rtns) {
                item = rtns[key];
                if ('name' in item && wsMethodBox.hasOwnProperty(item.name)) {
                    try {
                        if ('error' in item) {
                            wsMethodBox[item.name](item.error)
                        } else {
                            wsMethodBox[item.name](null, item.result)
                        }
                    } catch (err) {
                        console.error(err)
                    }
                }
            }
        }
    };

    wsMethodBox['pinpon.pin'] = function (err, result) {
        console.log('pinpon.pin', result)
    };
    wsMethodBox['pinpon.pon'] = function (err, result) {
        console.log('pinpon.pon', result)
    };
    ws.send(JSON.stringify({
        wsId, fns: [{randId: getRandomId(), name: 'pinpon.pin', prop: 3}]
    }));
})();

