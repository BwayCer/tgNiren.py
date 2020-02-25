'use strict';


(_ => {
    const helNiUsersStatus = document.querySelector('.cStatusInfo_niUsers');
    const helLatestStatus = document.querySelector('.cStatusInfo_latest');
    (async function checkStatus(errorCount) {
        let fetchResult;
        try {
            fetchResult = await fetch('/api/latestStatus', {
                method: 'POST',
                headers: new Headers({
                    'Content-Type': 'application/json'
                }),
                body: JSON.stringify({
                    method: 'latestStatus'
                }),
            });
        } catch (err) {
            alert('找不到主機');
            return;
        }

        let niUsersStatus = '';
        let latestStatus = '';

        if (fetchResult.status >= 500) {
            errorCount += 1;
            latestStatus = `${fetchResult.status} 主機錯誤`;
        } else {
            let data = await fetchResult.json();

            if (fetchResult.status >= 400) {
                errorCount += 1;
                latestStatus = data.message;
            } else {
                errorCount = 0;
                niUsersStatus = data.niUsersStatus;
                latestStatus = data.latestStatus;
                niUsersStatus = niUsersStatus !== null ? niUsersStatus : '---';
                latestStatus = latestStatus !== null ? latestStatus : '---';
            }
        }

        helNiUsersStatus.innerText = niUsersStatus;
        helLatestStatus.innerText = latestStatus;

        if (errorCount < 3) {
            setTimeout(checkStatus, 3000, errorCount);
        } else {
            helLatestStatus.innerText += ' (請試試重整網頁 (F5))';
        }
    })(0);
})();


(_ => {
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
            const payload = {
                method: 'paperSlipAction',
                forwardPeerList: roomIdsTxt.split(','),
                mainGroup: matchSourceLinkTxt[1],
                messageId: parseInt(matchSourceLinkTxt[2]),
            };
            let fetchResult;
            try {
                fetchResult = await fetch('/', {
                    method: 'POST',
                    headers: new Headers({
                        'Content-Type': 'application/json'
                    }),
                    body: JSON.stringify(payload),
                });
            } catch (err) {
                alert('找不到主機');
                return;
            }
            if (fetchResult.status !== 200) {
                console.log(fetchResult.status);
                return;
            }
            let data = await fetchResult.json();
            document.querySelector('.cStatusInfo_latest').innerText = data.message;
        })
    ;
})();

