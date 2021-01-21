'use strict';


let resizeEventManager = new EventIntervalManager('resize', 100, 300);

void function () {
    resizeEventManager.add(function () {
        let windowWidth = window.innerWidth;

        if (windowWidth < 1000) {
        } else {
        }
    });
}();

void function () {
    let helPageCtrl = document.querySelector('.pageCtrl');
    helPageCtrl.querySelector('.markShare').addEventListener('click', function () {
        if (navigator.share) {
            navigator.share({
                title: document.title,
                text: '關於我 - ' + document.querySelector('.resume_card_sign_name').textContent + '\n',
                url: location.href,
            })
            .catch((error) => console.log('Error sharing', error));
        }
    }); 
    helPageCtrl.querySelector('.markPrint').addEventListener('click', function () {
        window.print();
    }); 
}();

