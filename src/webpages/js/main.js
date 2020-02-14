'use strict';


(_ => {
    const helFormRoomIds = document.querySelector('.cPaperSlip_form_roomIds > .makeInput');

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
})();

