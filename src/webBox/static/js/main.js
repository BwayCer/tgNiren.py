'use strict';


(async _ => {
    const ws = new WebSocket('ws://' + document.domain + ':' + location.port + '/ws');
    await (function connectWs(ws) {
        ws.onopen = function () {
            ws.send('pin')
        };

        return new Promise(function (reject, resolve) {
            ws.onmessage = function (evt) {
                let receiveDatasTxt = evt.data;

                switch (receiveDatasTxt) {
                    case 'pon':
                        ws.send('register')
                        break
                    case 'register-ok':
                        ws.onopen = ws.onmessage = null;
                        reject('ok');
                        break
                }
            };
            setTimeout(function () {
                resolve('timeout');
            }, 10000);
        });
    })(ws);

    ws.onclose = function (evt) {
        alert('失去連線 請試試重整網頁 (F5)');
    };

    let wsMethodBox = {};
    ws.onmessage = function (evt) {
        const receiveDatasTxt = evt.data;
        console.log(receiveDatasTxt);

        const receiveDatas = JSON.parse(receiveDatasTxt)
        if (receiveDatas.constructor === Array) {
            let key, item, type;
            for (key in receiveDatas) {
                item = receiveDatas[key];
                if ('type' in item && wsMethodBox.hasOwnProperty(item.type)) {
                    try {
                        wsMethodBox[item.type](item);
                    } catch (err) {
                        console.error(err)
                    }
                }
            }
        }
    };

    (_ => {
        const helNiUsersStatus = document.querySelector('.cStatusInfo_niUsers');

        wsMethodBox['niUsersStatus.latestStatus'] = function (receive) {
            let niUsersStatus = receive.niUsersStatus;
            niUsersStatus = niUsersStatus !== null ? niUsersStatus : '---';

            helNiUsersStatus.innerText = niUsersStatus;
        };
        ws.send(JSON.stringify([{type: 'niUsersStatus.subscribe', prop: 'latestStatus'}]));
    })();

    (_ => {
        const helPaperSlipStatus = document.querySelector('.cPaperSlip_status');
        const helFormRoomIds = document.querySelector('.cPaperSlip_form_roomIds > .makeInput');
        const helFormSourceLink = document.querySelector('.cPaperSlip_form_sourceLink > .makeInput');

        function _csvParse(csvData) {
            let currMatch, currMatch_3;
            let fieldRegEx = new RegExp(
                '(?:\s*"((?:""|[^"])*)"\s*|\s*((?:""|[^",\r\n])*(?:""|[^"\s,\r\n]))?\s*)'
                    + '(,|[\r\n]+|$)',
                'g'
            );
            let rows = [];
            let row = [];

            for ( ; currMatch = fieldRegEx.exec(csvData) ; ) {
                row.push((currMatch[1] || '') + (currMatch[2] || ''));
                currMatch_3 = currMatch[3];

                if (currMatch_3 !== ',') {
                    rows.push(row);
                    row = [];
                }
                if (currMatch_3 === '') {
                    break;
                }
            }

            return rows;
        }
        document.querySelector('.cPaperSlip_form_roomIds_csvUpload > .makeInput')
            .addEventListener('change', async function (evt) {
                const file = this.files[0];
                if (file === null || file.name.substr(-4) !== '.csv') {
                    alert('請提供 csv 文件');
                    return;
                }
                let roomIds = [];
                _csvParse(await file.text()).forEach(function (lineList) {
                    lineList.forEach(function (val) {
                        if (val !== '') {
                            roomIds.push(val);
                        }
                    });
                });
                helFormRoomIds.value +=
                    (helFormRoomIds.value === '' ? '' : ',')
                    + roomIds.join(',')
                ;
            })
        ;

        wsMethodBox['adTool.paperSlip']
            = wsMethodBox['adTool.paperSlipAction']
            = function (receive) {
                console.log('adTool.paperSlip', receive);
                if (receive.code < 0) {
                    console.error('adTool.paperSlip', receive);
                }
                helPaperSlipStatus.innerText = receive.message;
            };
        let _regexWord = /\w/;
        let _regexSourceLink = /^https:\/\/t\.me\/([^\/]+)\/(\d+)$/;
        document.querySelector('.cPaperSlip_form_submit')
            .addEventListener('click', async function (evt) {
                evt.preventDefault();
                let roomIdsTxt = helFormRoomIds.value;
                if (!_regexWord.test(roomIdsTxt)) {
                    alert('請填寫用戶/群組 ID');
                    return;
                }
                let matchSourceLinkTxt = helFormSourceLink.value.match(_regexSourceLink);
                if (matchSourceLinkTxt === null) {
                    alert('來源鏈結格式錯誤');
                    return;
                }
                ws.send(JSON.stringify([{
                    type: 'adTool.paperSlip',
                    prop: {
                        forwardPeerList: roomIdsTxt.split(','),
                        mainGroup: matchSourceLinkTxt[1],
                        messageId: parseInt(matchSourceLinkTxt[2]),
                    },
                }]));
            })
        ;
    })();
})();


