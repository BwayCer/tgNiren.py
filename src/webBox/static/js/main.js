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
        const helFormPhone = document.querySelector('.cLogin_pop_form_phone > .markInput');
        const helFormVerifiedCode = document.querySelector('.cLogin_pop_form_verifiedCode > .markInput');
        const helFormPassword = document.querySelector('.cLogin_pop_form_password > .markInput');
        const helFormName = document.querySelector('.cLogin_pop_form_signup > .markInput');

        const helOtherSentBtn = document.querySelector('.cLogin_pop_form_verifiedCode_otherSentBtn');
        const helDeleteAccountBtn = document.querySelector('.cLogin_pop_form_password_deleteAccount');
        const helFormSubmitBtn = document.querySelector('.cLogin_pop_form_submit');
        const helFormResetBtn = document.querySelector('.cLogin_pop_form_reset');

        let interactiveLoginInfo = {
            prevRequest: null,
            hostStateCode: 0,
            stateCode: 0,
            phoneNumber: '',
            phoneCodeHash: '',
        };

        wsMethodBox['interactiveLogin.login']
            = wsMethodBox['interactiveLogin.sendCode']
            = wsMethodBox['interactiveLogin.verifiedCode']
            = wsMethodBox['interactiveLogin.verifiedPassword']
            = wsMethodBox['interactiveLogin.deleteAccount']
            = wsMethodBox['interactiveLogin.signup']
            = function (receive) {
                console.log('interactiveLogin', receive)

                if ('error' in receive) {
                    console.error(receive.error);
                    helLoginPopStatus.innerText = receive.error.message;
                    return;
                }

                interactiveLoginInfo.prevRequest = receive;
                helLoginPopStatus.innerText = receive.message;
                if (receive.code >= 0) {
                    interactiveLoginInfo.hostStateCode = receive.code;
                }

                // switch (receive.code) {
                //     case -3: // 登入錯誤
                //     case -2: // 互動錯誤
                //     case -1: // 程式錯誤
                //     case 1: // 驗證碼互動
                //     case 2: // 密碼互動
                //     case 4: // 登入/註冊成功
                // }
                switch (`c${String(receive.code)}_${receive.messageType}`) {
                    case 'c1_sendCode':
                    case 'c1_sendCodeAndNext':
                    case 'c1_sendCodeAndNextHasTimeout':
                        interactiveLoginInfo.stateCode = 1;
                        // interactiveLoginInfo.phoneNumber = receive.phoneNumber;
                        interactiveLoginInfo.phoneCodeHash = receive.phoneCodeHash;
                        break;
                    case 'c1_passwordNeeded':
                        interactiveLoginInfo.stateCode = 2;
                        break;
                    case 'c1_phoneNumberUnoccupied':
                        interactiveLoginInfo.stateCode = 3;
                        break;
                    case 'c2_registerAgain':
                        interactiveLoginInfo.stateCode = 3;
                        break;
                }
            }
        ;

        function htmlEntities(txt) {
            return txt
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
            ;
        }
        function pushLoginPop(msg) {
            let prevRequest = interactiveLoginInfo.prevRequest;
            if (prevRequest !== null) {
                helLoginPopStatus.innerHTML
                    = `${htmlEntities(prevRequest.message)}<br>${htmlEntities(msg)}`;
            } else {
                helLoginPopStatus.innerText = msg;
            }
        }

        helOtherSentBtn.addEventListener('click', async function (evt) {
            evt.preventDefault();

            if (interactiveLoginInfo.stateCode !== 1) {
                pushLoginPop('流程錯誤！ 無法點選以其他方式寄送功能。');
            }

            let phoneNumber = helFormPhone.value;
            if (phoneNumber === '') {
                pushLoginPop('流程錯誤！ 電話號碼丟失。');
                return;
            }

            let payload = {
                type: 'interactiveLogin.sendCode',
                prop: {
                    phoneNumber: phoneNumber,
                    phoneCodeHash: interactiveLoginInfo.phoneCodeHash,
                },
            };
            pushLoginPop('以其他方式寄送');
            ws.send(JSON.stringify([payload]));
        });
        helDeleteAccountBtn.addEventListener('click', async function (evt) {
            evt.preventDefault();

            if (interactiveLoginInfo.stateCode !== 2) {
                pushLoginPop('流程錯誤！ 無法點選重設帳戶功能。');
            }

            let phoneNumber = helFormPhone.value;
            if (phoneNumber === '') {
                pushLoginPop('流程錯誤！ 電話號碼丟失。');
                return;
            }

            let payload = {
                type: 'interactiveLogin.deleteAccount',
                prop: {
                    phoneNumber: phoneNumber,
                    phoneCodeHash: interactiveLoginInfo.phoneCodeHash,
                },
            };
            pushLoginPop('重設帳戶');
            ws.send(JSON.stringify([payload]));
        });
        helFormSubmitBtn.addEventListener('click', async function (evt) {
            evt.preventDefault();

            let stateCode = interactiveLoginInfo.stateCode;
            let phoneNumber = helFormPhone.value;
            if (phoneNumber === '') {
                if (stateCode === 0) {
                    pushLoginPop('請填寫電話號碼。');
                } else {
                    pushLoginPop('流程錯誤！ 電話號碼丟失。');
                }
                return;
            }

            let payload = {type: '', prop: null};

            if (interactiveLoginInfo.stateCode === 0) {
                payload.type = 'interactiveLogin.login';
                payload.prop = {phoneNumber};
                pushLoginPop(`登入 +${phoneNumber}`);
                ws.send(JSON.stringify([payload]));
                return;
            }

            let phoneCodeHash = interactiveLoginInfo.phoneCodeHash;
            let verifiedCode = helFormVerifiedCode.value;
            let password = helFormPassword.value;
            let name = helFormName.value;
            let methodName = '';

            if (phoneCodeHash === '') {
                pushLoginPop('流程錯誤！ 請先送出電話號碼。');
                return;
            }
            switch (interactiveLoginInfo.stateCode) {
                case 1:
                    if (verifiedCode === '') {
                        pushLoginPop('請輸入驗證碼。');
                        return;
                    }
                    methodName = 'verifiedCode';
                    payload.prop = {
                        phoneNumber, phoneCodeHash, verifiedCode
                    };
                    pushLoginPop(`送出 ${verifiedCode} 驗證碼`);
                    break;
                case 2:
                    if (password === '') {
                        pushLoginPop('請輸入密碼。');
                        return;
                    }
                    methodName = 'verifiedPassword';
                    payload.prop = {phoneNumber, phoneCodeHash, password};
                    pushLoginPop('送出密碼');
                    break;
                case 3:
                    if (name === '') {
                        pushLoginPop('請輸入新帳戶名稱。');
                        return;
                    }
                    methodName = 'signup';
                    payload.prop = {phoneNumber, phoneCodeHash, name};
                    pushLoginPop(`送出 ${name} 名稱`);
            }

            payload.type = 'interactiveLogin.' + methodName;
            ws.send(JSON.stringify([payload]));
        });
        helFormResetBtn.addEventListener('click', async function (evt) {
            evt.preventDefault();


            helFormPhone.value
                = helFormVerifiedCode.value
                = helFormPassword.value
                = helFormName.value
                = ''
            ;

            interactiveLoginInfo.prevRequest = null;
            interactiveLoginInfo.hostStateCode = 0;
            interactiveLoginInfo.stateCode = 0;
            interactiveLoginInfo.phoneNumber = '';
            interactiveLoginInfo.phoneCodeHash = '';
            pushLoginPop('重置成功');
        });
    })();

    (_ => {
        const helPaperSlipStatus = document.querySelector('.cPaperSlip_status');
        const helFormRoomIds = document.querySelector('.cPaperSlip_form_roomIds > .markInput');
        const helFormSourceLink = document.querySelector('.cPaperSlip_form_sourceLink > .markInput');

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
        document.querySelector('.cPaperSlip_form_roomIds_csvUpload > .markInput')
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


