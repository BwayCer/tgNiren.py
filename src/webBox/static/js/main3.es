'use strict';


const MDCRipple = mdc.ripple.MDCRipple;
const MDCList   = mdc.list.MDCList;
const MDCTabBar = mdc.tabBar.MDCTabBar;
const MDCDialog = mdc.dialog.MDCDialog;
const MDCTextField = mdc.textField.MDCTextField;

Array.from(document.querySelectorAll('.mdc-text-field'))
    .map(helMdcTarget => new MDCTextField(helMdcTarget));
Array.from(document.querySelectorAll('.mdc-fab, .mdc-button'))
    .map(helMdcTarget => new MDCRipple(helMdcTarget));
Array.from(document.querySelectorAll('.mdc-list'))
    .map(helMdcTarget => new MDCList(helMdcTarget));
Array.from(document.querySelectorAll('.mdc-list > li'))
    .map(helMdcTarget => new MDCRipple(helMdcTarget));

Array.from(document.querySelectorAll('.cMdcTab')).forEach(function (helCMdcTab) {
    const tabBar = new MDCTabBar(helCMdcTab.querySelector('.mdc-tab-bar'));

    let helPanelWrap = helCMdcTab.querySelector('.cMdcTab_panelWrap');
    let panelHelAll = helPanelWrap.querySelectorAll('.cMdcTab_panel');

    tabBar.listen('MDCTabBar:activated', function(evt) {
        helPanelWrap.querySelector('.cMdcTab_panel.onActive')
            .classList.remove('onActive');
        panelHelAll[evt.detail.index].classList.add('onActive');
    });
});

Array.from(document.querySelectorAll('.cMdcDialog')).forEach(function (helCMdcDialog) {
    const helBtn = helCMdcDialog.querySelector('.cMdcDialog_btn')
    const helDialog = helCMdcDialog.querySelector('.cMdcDialog_dialog')
    const dialog = new MDCDialog(helDialog);
    // https://github.com/material-components/material-components-web/tree/master/packages/mdc-dialog#javascript-instantiation
    // const list = new MDCList(helDialog.querySelector('.mdc-list'));

    dialog.listen('MDCDialog:accept', function() {
        console.log('accepted');
    });
    dialog.listen('MDCDialog:cancel', function() {
        console.log('canceled');
    });
    dialog.listen('MDCDialog:closing', function() {
        console.log('closing');
    });
    // dialog.listen('MDCDialog:opened', () => {
        // // list.layout();
        // // console.log('opened');
    // });

    window.emitt = function () {
        // dialog.lastFocusedTarget = evt.target;
        dialog.open();
        // dialog.emit('MDCDialog:opened')
    };
    helBtn.addEventListener('click', function () {
        // dialog.lastFocusedTarget = evt.target;
        dialog.open();
        // dialog.emit('MDCDialog:opened')
    }, false);
});

