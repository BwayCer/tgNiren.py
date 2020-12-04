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
        console.log('receive:', receiveDatasTxt);

        if (receiveDatasTxt === 'pon') {
            if (wsMethodBox.hasOwnProperty('pon')) {
                try {
                    wsMethodBox['pon']();
                } catch (err) {
                    console.error(err);
                }
            }
            return;
        }

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
                            wsMethodBox[item.name](item.error);
                        } else if ('result' in item) {
                            wsMethodBox[item.name](null, item.result);
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

    (_ => {
        let prevTimestamp = 0;
        let isFocus = true;
        let isCanPin = true;

        wsMethodBox['pon'] = function () {
            isCanPin = true;
        };

        (function tmp() {
            if (isFocus && isCanPin) {
                isCanPin = false;
                prevTimestamp = +new Date();
                ws.send('pin');
            }
            setTimeout(tmp, 1200000);
        })();

        window.addEventListener('blur', function () {
            isFocus = false;
        });
        window.addEventListener('focus', function () {
            isFocus = true;
            let now = +new Date();
            if (now - prevTimestamp > 2400000) {
                prevTimestamp = now;
                ws.send('pin');
            }
        });
    })();

    (_ => {
        const helNiUsersStatus = document.querySelector('.cStatusInfo_niUsers');

        wsMethodBox['niUsersStatus.latestStatus'] = function (err, result) {
            let niUsersStatus = result.niUsersStatus;
            niUsersStatus = niUsersStatus !== null ? niUsersStatus : '---';

            helNiUsersStatus.innerText = niUsersStatus;
        };
        ws.send(JSON.stringify({wsId, fns: [
            {randId: getRandomId(), name: 'ws.subscribe', prop: 'latestStatus'},
        ]}));
    })();

    (_ => {
        const helLoginPopStatus = document.querySelector('.cLogin_status');
        const helFormPhone = document.querySelector('.cLogin_form_phone > .markInput');
        const helFormVerifiedCode = document.querySelector('.cLogin_form_verifiedCode > .markInput');
        const helFormPassword = document.querySelector('.cLogin_form_password > .markInput');
        const helFormName = document.querySelector('.cLogin_form_signup > .markInput');

        const helOtherSentBtn = document.querySelector('.cLogin_form_verifiedCode_otherSentBtn');
        const helUseQrLoginBtn = document.querySelector('.cLogin_form_verifiedCode_useQrLogin');
        const helDeleteAccountBtn = document.querySelector('.cLogin_form_password_deleteAccount');
        const helFormSubmitBtn = document.querySelector('.cLogin_form_submit');
        const helFormResetBtn = document.querySelector('.cLogin_form_reset');

        let loginQrcode = null;
        if (typeof window.QRCode !== 'object') {
            let helQrcodeBox = document.querySelector('.cLogin_qrcodeBox');
            helQrcodeBox.style.display = 'none';
            loginQrcode = {
                _qrcode: new QRCode(helQrcodeBox, {
                      text: '',
                      width: 128,
                      height: 128,
                      colorDark : '#000',
                      colorLight : '#fff',
                      correctLevel : QRCode.CorrectLevel.L
                }),
                update(url) {
                    this._qrcode.makeCode(url);
                    helQrcodeBox.style.display = 'block';
                },
                clear() {
                    helQrcodeBox.style.display = 'none';
                }
            };
        }

        let interactiveLoginInfo = {
            prevRequest: null,
            hostStateCode: 0,
            stateCode: 0,
            phoneNumber: '',
            phoneCodeHash: '',
        };

        wsMethodBox['interactiveLogin.login']
            = wsMethodBox['interactiveLogin.sendCode']
            = wsMethodBox['interactiveLogin.qrLogin']
            = wsMethodBox['interactiveLogin.verifiedCode']
            = wsMethodBox['interactiveLogin.verifiedPassword']
            = wsMethodBox['interactiveLogin.deleteAccount']
            = wsMethodBox['interactiveLogin.signup']
            = function (err, result) {
                if (err) {
                    console.error(`${err.name}: ${err.message}`);
                    helLoginPopStatus.innerText = err.message;
                    return;
                }

                interactiveLoginInfo.prevRequest = result;
                helLoginPopStatus.innerText = result.message;
                if (result.code >= 0) {
                    interactiveLoginInfo.hostStateCode = result.code;
                }

                // switch (result.code) {
                //     case -3: // 登入錯誤
                //     case -2: // 互動錯誤
                //     case -1: // 程式錯誤
                //     case 1: // 驗證碼互動
                //     case 2: // 密碼互動
                //     case 4: // 登入/註冊成功
                // }
                switch (`c${String(result.code)}_${result.messageType}`) {
                    case 'c1_sendCode':
                    case 'c1_sendCodeAndNext':
                    case 'c1_sendCodeAndNextHasTimeout':
                        interactiveLoginInfo.stateCode = 1;
                        // interactiveLoginInfo.phoneNumber = result.phoneNumber;
                        interactiveLoginInfo.phoneCodeHash = result.phoneCodeHash;
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
                    case 'c5_qrToken':
                        loginQrcode.update(result.token);
                        break;
                    case 'c4_loggedin':
                    case 'c4_successLogin':
                    case 'c5_qrTokenExpired':
                    case 'c-2_qrTokenExpired':
                    case 'c-2_qrUnknownType':
                        loginQrcode.clear();
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
                randId: getRandomId(),
                name: 'interactiveLogin.sendCode',
                prop: {
                    phoneNumber: phoneNumber,
                    phoneCodeHash: interactiveLoginInfo.phoneCodeHash,
                },
            };
            pushLoginPop('以其他方式寄送');
            ws.send(JSON.stringify({wsId, fns: [payload]}));
        });
        helUseQrLoginBtn.addEventListener('click', function (evt) {
            evt.preventDefault();

            if (interactiveLoginInfo.stateCode < 1) {
                pushLoginPop('流程錯誤！ 請先送出電話號碼。');
            }

            if (loginQrcode === null) {
                pushLoginPop('不支援 QR 碼登入！');
            }

            let phoneNumber = helFormPhone.value;
            if (phoneNumber === '') {
                pushLoginPop('流程錯誤！ 電話號碼丟失。');
                return;
            }

            let payload = {
                randId: getRandomId(),
                name: 'interactiveLogin.qrLogin',
                prop: {
                    phoneNumber: phoneNumber,
                    phoneCodeHash: interactiveLoginInfo.phoneCodeHash,
                },
            };
            pushLoginPop('使用 QR 碼登入');
            ws.send(JSON.stringify({wsId, fns: [payload]}));
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
                randId: getRandomId(),
                name: 'interactiveLogin.deleteAccount',
                prop: {
                    phoneNumber: phoneNumber,
                    phoneCodeHash: interactiveLoginInfo.phoneCodeHash,
                },
            };
            pushLoginPop('重設帳戶');
            ws.send(JSON.stringify({wsId, fns: [payload]}));
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

            let payload = {randId: getRandomId(), type: '', prop: null};

            if (interactiveLoginInfo.stateCode === 0) {
                payload.name = 'interactiveLogin.login';
                payload.prop = {phoneNumber};
                pushLoginPop(`登入 +${phoneNumber}`);
                ws.send(JSON.stringify({wsId, fns: [payload]}));
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

            payload.name = 'interactiveLogin.' + methodName;
            ws.send(JSON.stringify({wsId, fns: [payload]}));
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

    class LogRecord {
        constructor() {
            this.elemTextarea = document.createElement('textarea');
            this.elemTextarea.style.display = 'none';
            this._elemLogArea.appendChild(this.elemTextarea);
        }

        _elemLogArea = document.querySelector('.cLog');

        push(txt) {
            let now = new Date();
            let elemTextarea = this.elemTextarea;

            if (this.elemTextarea.style.display === 'none') {
                this.elemTextarea.style.display = null;
            }

            elemTextarea.value =
                (elemTextarea.value !== '' ? elemTextarea.value + '\n\n' : '')
                + `-> ${this._getNowTimeStampingUtc()}\n${txt}`
            ;
            elemTextarea.scrollTo(0, elemTextarea.scrollHeight);
        }

        _getNowTimeStampingUtc() {
            let assignDate = new Date();
            var timezoneOffset = assignDate.getTimezoneOffset();
            let timeMsUtc = +assignDate + timezoneOffset * 60000;
            let dateUtc = new Date(timeMsUtc);
            return this._setLengthNum(dateUtc.getFullYear(), 4)
                + '-' + this._setLengthNum(dateUtc.getMonth() + 1, 2)
                + '-' + this._setLengthNum(dateUtc.getDate(), 2)
                + ' ' + this._setLengthNum(dateUtc.getHours(), 2)
                + ':' + this._setLengthNum(dateUtc.getMinutes(), 2)
                + ':' + this._setLengthNum(dateUtc.getSeconds(), 2)
                + '.' + this._setLengthNum(dateUtc.getMilliseconds(), 3)
            ;
        }

        _setLengthNum(numChoA, length) {
            let strChoA = numChoA.toString();
            let loop = length - strChoA.length;
            let addStr = '';
            for (; loop > 0 ; loop--) addStr += '0';
            return addStr + strChoA;
        }
    }

    (_ => {
        const helPaperSlipStatus = document.querySelector('.cGetParticipants_status');
        const helGetParticipantsStatus = document.querySelector('.cGetParticipants_status');
        const helFormRoomId = document.querySelector('.cGetParticipants_form_roomId > .markInput');
        const helFormOffsetDays = document.querySelector('.cGetParticipants_form_offsetDays > .markInput');

        const helFormSubmitBtn = document.querySelector('.cGetParticipants_form_submit');

        wsMethodBox['adTool.getParticipants']
            = wsMethodBox['adTool.getParticipantsAction']
            = function (err, result) {
                if (err) {
                    console.error(`${err.name}: ${err.message}`);
                    helGetParticipantsStatus.innerText = err.message;
                    return;
                }

                console.log('adTool.getParticipants', result)

                if (result.code < 0) {
                    console.error('adTool.getParticipants', result);
                }
                helGetParticipantsStatus.innerText = result.message;

                if (result.code === 1 && result.participantIds.length > 0) {
                    let url = '';
                    try {
                        let csvContent = `${result.participantIds.join(',\n')}`;
                        url = window.URL.createObjectURL(
                            new Blob([csvContent], {type: 'text/plain'})
                        );

                        let downloadLink = document.createElement('a');
                        downloadLink.href = url;
                        downloadLink.download = 'participantUserNames.csv';
                        document.body.appendChild(downloadLink);
                        downloadLink.click();
                        document.body.removeChild(downloadLink);
                    } finally {
                        if (url !== '') {
                            window.URL.revokeObjectURL(url);
                        }
                    }
                }
            }
        ;
        let _regexWord = /\w/;
        helFormSubmitBtn.addEventListener('click', async function (evt) {
            evt.preventDefault();
            let roomIdTxt = helFormRoomId.value;
            if (!_regexWord.test(roomIdTxt)) {
                alert('請填寫群組 ID');
                return;
            }
            let offsetDaysNum = Number(helFormOffsetDays.value);
            if (!(offsetDaysNum > 0)) {
                alert('請填寫過濾期間 (其值須大於 0)');
                return;
            }
            ws.send(JSON.stringify({wsId, fns: [{
                randId: getRandomId(),
                name: 'adTool.getParticipants',
                prop: {
                    groupPeer: roomIdTxt,
                    offsetDays: offsetDaysNum,
                },
            }]}));
        });
    })();

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

    (_ => {
        const helTuckUserStatus = document.querySelector('.cTuckUser_status');
        const helFormUserIds = document.querySelector('.cTuckUser_form_userIds > .markInput');
        const helFormOurGroup = document.querySelector('.cTuckUser_form_ourGroup > .markInput');

        document.querySelector('.cTuckUser_form_userIds_csvUpload > .markInput')
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
                helFormUserIds.value +=
                    (helFormUserIds.value === '' ? '' : ',')
                    + roomIds.join(',')
                ;
            })
        ;

        let logRecord = new LogRecord();

        wsMethodBox['adTool.tuckUser']
            = wsMethodBox['adTool.tuckUserAction']
            = function (err, result) {
                if (err) {
                    console.error(`${err.name}: ${err.message}`);
                    helTuckUserStatus.innerText = err.message;
                    return;
                }

                if (result.code < 0) {
                    console.error('adTool.tuckUser', result);
                }
                helTuckUserStatus.innerText = result.message;
                logRecord.push(result.message);
            }
        ;
        let _regexWord = /\w/;
        document.querySelector('.cTuckUser_form_submit')
            .addEventListener('click', async function (evt) {
                evt.preventDefault();

                let userIdsTxt = helFormUserIds.value;
                if (!_regexWord.test(userIdsTxt)) {
                    alert('請填寫用戶 ID');
                    return;
                }
                let toGroupTxt = helFormOurGroup.value;
                if (!_regexWord.test(toGroupTxt)) {
                    alert('請填寫群組 ID');
                    return;
                }

                logRecord.push('已送出拉人入群請求');

                ws.send(JSON.stringify({wsId, fns: [{
                    randId: getRandomId(),
                    name: 'adTool.tuckUser',
                    prop: {
                        userPeerList: userIdsTxt.split(','),
                        toGroupPeer: toGroupTxt,
                    },
                }]}));
            })
        ;
    })();

    (_ => {
        const helPaperSlipStatus = document.querySelector('.cPaperSlip_status');
        const helFormRoomIds = document.querySelector('.cPaperSlip_form_roomIds > .markInput');
        const helFormSourceLink = document.querySelector('.cPaperSlip_form_sourceLink > .markInput');

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

        let logRecord = new LogRecord();

        wsMethodBox['adTool.paperSlip']
            = wsMethodBox['adTool.paperSlipAction']
            = function (err, result) {
                if (err) {
                    console.error(`${err.name}: ${err.message}`);
                    helPaperSlipStatus.innerText = err.message;
                    return;
                }

                if (result.code < 0) {
                    console.error('adTool.paperSlip', result);
                }
                helPaperSlipStatus.innerText = result.message;
                logRecord.push(result.message);
            }
        ;
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

                logRecord.push('已送出廣告炸群請求');

                ws.send(JSON.stringify({wsId, fns: [{
                    randId: getRandomId(),
                    name: 'adTool.paperSlip',
                    prop: {
                        forwardPeerList: roomIdsTxt.split(','),
                        mainGroup: matchSourceLinkTxt[1],
                        messageId: parseInt(matchSourceLinkTxt[2]),
                    },
                }]}));
            })
        ;
    })();
})();

