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
      || receiveDatas.wsId !== wsId
    ) {
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

  function readableDate(dt) {
    if (! dt instanceof Date) {
      throw TypeError('The argument is not `Date` type.');
    }

    return readableDate._setLengthNum(dt.getFullYear(), 4)
      + '-' + readableDate._setLengthNum(dt.getMonth() + 1, 2)
      + '-' + readableDate._setLengthNum(dt.getDate(), 2)
      + ' ' + readableDate._setLengthNum(dt.getHours(), 2)
      + ':' + readableDate._setLengthNum(dt.getMinutes(), 2)
      + ':' + readableDate._setLengthNum(dt.getSeconds(), 2)
      + '.' + readableDate._setLengthNum(dt.getMilliseconds(), 3)
    ;
  }
  readableDate._setLengthNum = function (numChoA, length) {
    let strChoA = numChoA.toString();
    let loop = length - strChoA.length;
    let addStr = '';
    for (; loop > 0 ; loop--) addStr += '0';
    return addStr + strChoA;
  };


  (_ => {
    const elemAllRespondStatus = document.querySelector('.cAllRespond_status');
    const elemAllRespondLog = document.querySelector('.cAllRespond_log');
    const elemAllRespondDialog = document.querySelector('.cAllRespond_dialog');

    class LogRecord {
      constructor() {
        this.elemTextarea = document.createElement('textarea');
        this.elemTextarea.style.display = 'none';
        this._elemLogArea.appendChild(this.elemTextarea);
      }

      _elemLogArea = elemAllRespondLog;

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
        return readableDate(dateUtc);
      }
    }

    class Dialog {
      constructor(dialogInfos = []) {
        this.dialogInfos = dialogInfos;
      }

      show() {
        let dialogInfos = this.dialogInfos;
        for (let idx = 0, len = dialogInfos.length; idx < len; idx++) {
          let dialogInfo = dialogInfos[idx];
          let elemPre = document.createElement('pre');
          elemPre.dataset.idx = idx;
          let dtMsg = new Date(dialogInfo.timestamp);
          let txt = readableDate(dtMsg) + '\n';
          txt += `${dialogInfo.chatTypeName}(${dialogInfo.chatName})`;
          if (dialogInfo.fromTypeName !== null) {
            txt += `: ${dialogInfo.fromTypeName}(${dialogInfo.fromName})`;
          }
          txt += ` -> ${dialogInfo.myId}\n`;
          txt += `  Message:\n${dialogInfo.message}`;
          elemPre.innerText = txt;
          elemAllRespondDialog.appendChild(elemPre);
        }
      }

      update(dialogInfos) {
        if (! dialogInfos instanceof Array) {
          return;
        }
        this.dialogInfos.length = 0;
        if (dialogInfos.length > 0) {
          this.dialogInfos.push(...dialogInfos);
          this.dialogInfos.sort((prev, next) => next.timestamp - prev.timestamp);
        }
        this.show();
      }

      add(dialogInfos) {
        if (! dialogInfos instanceof Array || dialogInfos.length <= 0) {
          return;
        }
        this.dialogInfos.push(...dialogInfos);
        this.dialogInfos.sort((prev, next) => next.timestamp - prev.timestamp);
        this.show();
      }
    }

    let logRecord = new LogRecord();
    let dialog = new Dialog();

    wsMethodBox['dialog.allRespond']
      = wsMethodBox['dialog.allRespondAction']
      = function (err, result) {
        if (err) {
          console.error(`${err.name}: ${err.message}`);
          elemAllRespondStatus.innerText = err.message;
          return;
        }

        elemAllRespondStatus.innerText = result.message;
        logRecord.push(result.message);

        console.log(result);
        let respondDialogInfo;
        switch (`c${String(result.code)}_${result.messageType}`) {
          case 'c1_addNew':
            respondDialogInfo = result.respondDialogInfo;
            dialog.add(respondDialogInfo.addDialogs);
            break;
          case 'c1_executing':
            respondDialogInfo = result.respondDialogInfo;
            dialog.add(respondDialogInfo.addDialogs);
            break;
          case 'c2_complete':
          case 'c2_record':
            respondDialogInfo = result.respondDialogInfo;
            dialog.update(respondDialogInfo.dialogs);
            break;
          case 'c2_noNiUser':
            dialog.update([]);
            break;
        }
      }
    ;

    elemAllRespondStatus.innerText = '請求已送出';
    logRecord.push('讀取對話紀錄請求已送出');

    ws.send(JSON.stringify({wsId, fns: [{
      randId: getRandomId(),
      name: 'dialog.allRespond',
      prop: null,
    }]}));
  })();
})();

