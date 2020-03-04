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

    wsMethodBox['pinpon.pin'] = function (receive) {
        console.log('pinpon.pin', receive)
    };
    wsMethodBox['pinpon.pon'] = function (receive) {
        console.log('pinpon.pon', receive)
    };
    ws.send(JSON.stringify([{type: 'pinpon.pin', prop: 3}]));

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
        const helLoginPopStatus = document.querySelector('.cLogin_pop_statusInfo');
        const helFormPhone = document.querySelector('.cLogin_pop_form_phone > .makeInput');
        const helFormVerifiedCode = document.querySelector('.cLogin_pop_form_verifiedCode > .makeInput');

        let host_phoneNumber = '';
        let host_phoneCodeHash = '';

        wsMethodBox['interactiveLogin.sendCode']
            = wsMethodBox['interactiveLogin.verifiedCode']
            = function (receive) {
                if ('error' in receive) {
                    console.error(receive.error);
                    helLoginPopStatus.innerText = receive.error.message;
                }

                console.log('interactiveLogin', receive)
                switch (receive.code) {
                    case -3: // 登入失敗
                    case -2: // 登入的仿用戶與主機留存仿用戶不相同
                        host_phoneNumber = receive.phoneNumber;
                        helLoginPopStatus.innerText = receive.message;
                        break;
                    case -1:
                        host_phoneNumber = '';
                        helLoginPopStatus.innerText = receive.message;
                        break;
                    case 2:
                        host_phoneNumber = receive.phoneNumber;
                        host_phoneCodeHash = receive.phoneCodeHash;
                        helLoginPopStatus.innerText = receive.message;
                        break;
                    case 1: // 仿用戶已登入
                    case 3: // 仿用戶登入成功
                        host_phoneNumber = host_phoneCodeHash = '';
                        helLoginPopStatus.innerText = receive.message;
                        break;
                }
            }
        ;

        let _regexWord = /\w/;
        let _regexSourceLink = /^https:\/\/t\.me\/([^\/]+)\/(\d+)$/;
        document.querySelector('.cLogin_pop_form_submit')
            .addEventListener('click', async function (evt) {
                evt.preventDefault();
                let phoneTxt = helFormPhone.value;
                let verifiedCodeTxt = helFormVerifiedCode.value;

                if (phoneTxt === '') {
                    helLoginPopStatus.innerText = '請填寫手機號碼';
                    return;
                }
                if (verifiedCodeTxt !== '' && host_phoneCodeHash === '') {
                    helLoginPopStatus.innerText
                        = '流程錯誤！ 請先送出手機號碼，再送出驗證號碼。';
                    return;
                }

                let payload = {
                    type: '',
                    prop: null,
                };
                if (verifiedCodeTxt === '') {
                    payload['type'] = 'interactiveLogin.sendCode';
                    payload['prop'] = {
                        phoneNumber: phoneTxt,
                    }
                } else {
                    payload['type'] = 'interactiveLogin.verifiedCode';
                    payload['prop'] = {
                        phoneNumber: phoneTxt,
                        phoneCodeHash: host_phoneCodeHash,
                        verifiedCode: verifiedCodeTxt,
                    }
                }

                ws.send(JSON.stringify([payload]));
            })
        ;
    })();

    (_ => {
        const helPaperSlipStatus = document.querySelector('.cPaperSlip_status');
        const helFormRoomIds = document.querySelector('.cPaperSlip_form_roomIds > .makeInput');
        const helFormSourceLink = document.querySelector('.cPaperSlip_form_sourceLink > .makeInput');

        function _csvParse(csvData) {
            let currMatch, currMatch_3;
            let fieldRegEx = /(?:\s*"((?:""|[^"])*)"\s*|\s*((?:""|[^",\r\n])*(?:""|[^"\s,\r\n]))?\s*)(,|[\r\n]+|$)/g
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


