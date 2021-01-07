#!/usr/bin/env python3


import typing
import os
import asyncio
import utils.novice as novice
from tgkream.tgTool import knownError, telethon, TgDefaultInit, TgBaseTool
from tgkream.tgSimple import TgDefaultInit, TgSimple


def run(args: list, _dirpy: str, _dirname: str):
    asyncio.run(asyncRun(args, _dirpy, _dirname))

async def asyncRun(args: list, _dirpy: str, _dirname: str) -> list:
    if len(args) > 1:
        subcmd = args[1]
        newArgs = [args[0], *args[2:]]
        if subcmd == 'getAllRespond':
            return await _run_getAllRespond(newArgs, _dirpy, _dirname)

    print('Usage: <subcmd (getAllRespond)>')
    os._exit(1)

async def _run_getAllRespond(args: list, _dirpy: str, _dirname: str) -> list:
    tgTool = TgDefaultInit(
        TgBaseTool,
        clientCount = 0,
        papaPhone = novice.py_env['papaPhoneNumber']
    )

    chanDataNiUsers = tgTool.chanDataNiUsers
    usablePhones = chanDataNiUsers.getUsablePhones()
    niUsers = chanDataNiUsers.chanData.data['niUsers']
    bandPhones = niUsers['bandList']
    lockPhones = niUsers['lockList']
    niUsers = None
    allCount = len(usablePhones)

    for idx in range(allCount):
        phoneNumber = usablePhones[idx]
        if phoneNumber in bandPhones or phoneNumber in lockPhones:
            continue
        client = await tgTool.login(phoneNumber)
        tgTool.clientCount += 1

    tgDialogInfos = []
    dialogInfos = []
    async for clientInfo in tgTool.iterPickClient(1, 1):
        readableIdx = idx + 1
        myId = clientInfo['id']
        client = clientInfo['client']

        try:
            dialogs = await client(telethon.functions.messages.GetDialogsRequest(
                offset_date = None,
                offset_id = 0,
                offset_peer = telethon.types.InputPeerEmpty(),
                limit = 100,
                hash = 0
            ))
        except Exception as err:
            if knownError.has('GetDialogsRequest', err):
                errTypeName = err.__class__.__name__
                errMsg = knownError.getMsg('GetDialogsRequest', err)
            else:
                errTypeName = type(err)
                errMsg = err

            print('from {} {} get {} Error: {}'.format(
                'client(messages.GetDialogsRequest)', myId, errTypeName, errMsg
            ))

            continue

        if type(dialogs) == telethon.types.messages.DialogsNotModified:
            continue

        for message in dialogs.messages:
            if type(message) != telethon.types.Message:
                continue

            dialogInfo = await _getDialogInfo(
                tgTool, message, dialogs.chats, dialogs.users
            )
            if dialogInfo == None:
                continue

            dialogInfo['myId'] = myId

            if dialogInfo['entityId'] == 777000:
                tgDialogInfos.append(dialogInfo)
            else:
                dialogInfos.append(dialogInfo)

    for dialogInfo in [*dialogInfos, *tgDialogInfos]:
        print('notify: {}{} -> {}\n  Message:\n{}\n\n'.format(
            '{}({})'.format(dialogInfo['chatTypeName'], dialogInfo['chatName']),
            (': {}({})'.format(dialogInfo['fromTypeName'], dialogInfo['fromName']) \
                if dialogInfo['fromTypeName'] != None else ''
            ),
            dialogInfo['myId'],
            dialogInfo['message']
        ))


async def _getDialogInfo(
        tgTool: TgBaseTool,
        message: telethon.types.Message,
        chats: list,
        users: list) -> typing.Union[None, dict]:
    if message.out:
        return None

    peerEntity = _findPeer(message.peer_id, chats, users)
    if peerEntity == None:
        return None

    peerInfo = await tgTool.parsePeer(peerEntity)

    if peerInfo['isBot'] or peerInfo['isChannel']:
        return None

    if message.from_id == None:
        fromPeerInfo = {
            'chatTypeName': None,
            'name': None,
        }
    else:
        fromPeerEntity = _findPeer(message.from_id, chats, users)
        if peerEntity == None:
            return None

        fromPeerInfo = await tgTool.parsePeer(fromPeerEntity)

        if fromPeerInfo['isBot']:
            return None

    return {
        'entityId': peerInfo['id'],
        'entityAccessHash': peerInfo['accessHash'],
        'entityTypeName': peerInfo['entityTypeName'],
        'chatTypeName': peerInfo['chatTypeName'],
        'chatName': peerInfo['name'],
        'fromTypeName': fromPeerInfo['chatTypeName'],
        'fromName': fromPeerInfo['name'],
        'message':
            ('(有媒體訊息) ' if message.media != None else '')
            + message.message
        ,
    }

def _findPeer(
        peer: typing.Union[
            telethon.types.PeerChannel,
            telethon.types.PeerChat,
            telethon.types.PeerUser,
        ],
        chats: list,
        users: list) -> typing.Union[
            None,
            telethon.types.Chat,
            telethon.types.User,
            telethon.types.Channel,
        ]:
    peerType = type(peer)
    chatList = ''
    chatId = 0
    if peerType == telethon.types.PeerChannel:
        chatList = chats
        chatId = peer.channel_id
    elif peerType == telethon.types.PeerChat:
        chatList = chats
        chatId = peer.chat_id
    elif peerType == telethon.types.PeerUser:
        chatList = users
        chatId = peer.user_id

    for chat in chatList:
        chatType = type(chat)
        if chatType == telethon.types.Chat \
                or chatType == telethon.types.Channel \
                or chatType == telethon.types.User:
            if chat.id == chatId:
                return chat

    return None

