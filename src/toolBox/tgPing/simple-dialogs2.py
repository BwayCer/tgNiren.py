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

async def asyncRun2(args: list, _dirpy: str, _dirname: str) -> list:
    if len(args) < 2:
        raise ValueError('Usage: <phoneNumber>')

    phoneNumber = args[1]

    tgTool = TgDefaultInit(TgSimple)
    client = await tgTool.login(phoneNumber)

    if client == None:
        raise Exception('Failed Login')

    try:
        last_date = None
        chunk_size = 200

        dialogs = await client(telethon.functions.messages.GetDialogsRequest(
            offset_date = last_date,
            offset_id = 0,
            offset_peer = telethon.types.InputPeerEmpty(),
            limit = chunk_size,
            hash = 0
        ))

      # Message(id=76460, to_id=PeerUser(user_id=281634169), date=datetime.datetime(2020, 11, 5, 5, 44, 28, tzinfo=datetime.timezone.utc),
      # message="Login code: 81220. Do not give this code to anyo
              # ne, even if they say they are from Telegram!\n\nThis code can be used to log in to your Telegram account. We never ask it for anything else.\n\nIf you didn't request this code by trying to l
              # og in on another device, simply ignore this message.",
              # out=False, mentioned=False, media_unread=False, silent=False, post=False, from_scheduled=False, legacy=False, edit_hide=False,
              # from_id=777000,
              # fwd_from=None, via_bot_id=None, reply_to_msg_id=None, media=None, reply_markup=None, entities=[MessageEntityBold(offset=0, length=11),
                  # MessageEntityBold(offset=22, length=3)], views=
              # None, edit_date=None, post_author=None, grouped_id=None, restriction_reason=[])
          # message: Login code: 81220. Do not give this code to anyone, even if they say they are from Telegram!

        print('dialogs')
        for item in getattr(dialogs, 'dialogs'):
            print('  {}'.format(item))
        print()

        print('message')
        for message in dialogs.messages:
            print(message)
            if message.from_id != 777000:
                continue

            print('  {}'.format(message))
            print('    message: {}'.format(message.message))
            print()

        return

        groups = []
        channels = []
        users = []
        bots = []

        for chat in dialogs.chats:
            if not type(chat) == telethon.types.Channel:
                continue
            if chat.megagroup == True:
                groups.append(chat)
            else:
                channels.append(chat)

        for user in dialogs.users:
            if user.bot == True:
                bots.append(user)
            else:
                users.append(user)

        print('groups:')
        for group in groups:
            print(group)
            print()
        print()
        print('channels:')
        for group in channels:
            print(group)
            print()
        print()
        print('users:')
        for group in users:
            print(group)
            print()
        print()
        print('bots:')
        for group in bots:
            print(group)
            print()
        print()


        # for chatList in [groups, channels, users, bots]:
            # for chat in chatList:
                # if chat.username != None:
                    # print('https://t.me/{}'.format(chat.username))

        # print('groups:')
        # for group in groups:
            # if group.username != None:
                # print('https://t.me/{}'.format(group.username))
        # print()
        # print('bots:')
        # for bot in bots:
            # if bot.username != None:
                # print('https://t.me/{}'.format(bot.username))
    except Exception as err:
        raise err

# Dialogs(
#     dialogs=[
#         Dialog(peer=PeerUser(user_id=777000), top_message=14, read_inbox_max_id=13, read_outbox_max_id=0, unread_count=1, unread_mentions_count=0, notify_settings=PeerNotifySettings(show_previews=None, silent=None, mute_until=None, sound=None), pinned=False, unread_mark=False, pts=None, draft=None, folder_id=None),
#         Dialog(peer=PeerChannel(channel_id=1224462889), top_message=1, read_inbox_max_id=1, read_outbox_max_id=0, unread_count=0, unread_mentions_count=0, notify_settings=PeerNotifySettings(show_previews=None, silent=None, mute_until=None, sound=None), pinned=False, unread_mark=False, pts=2, draft=None, folder_id=None),
#         Dialog(peer=PeerUser(user_id=1264065847), top_message=8, read_inbox_max_id=8, read_outbox_max_id=3, unread_count=0, unread_mentions_count=0, notify_settings=PeerNotifySettings(show_previews=None, silent=None, mute_until=None, sound=None), pinned=False, unread_mark=False, pts=None, draft=None, folder_id=None),
#         Dialog(peer=PeerUser(user_id=1116430935), top_message=2, read_inbox_max_id=12, read_outbox_max_id=0, unread_count=0, unread_mentions_count=0, notify_settings=PeerNotifySettings(show_previews=True, silent=False, mute_until=datetime.datetime(1970, 1, 1, 0, 0, tzinfo=datetime.timezone.utc), sound='default'), pinned=False, unread_mark=False, pts=None, draft=None, folder_id=None)
#     ],
#     messages=[
#         Message(
#             id=14,
#             to_id=PeerUser(user_id=1116430935),
#             date=datetime.datetime(2020, 9, 11, 7, 1, 22, tzinfo=datetime.timezone.utc),
#             message="Login code: 51474. Do not give this code to anyone, even if they say they are from Telegram!\n\nThis code can be used to log in to your Telegram account. We never ask it for anything else.\n\nIf you didn't request this code by trying to log in on another device, simply ignore this message.",
#             out=False, mentioned=False, media_unread=False, silent=True, post=False, from_scheduled=False, legacy=False, edit_hide=False, from_id=777000, fwd_from=None, via_bot_id=None, reply_to_msg_id=None, media=None, reply_markup=None, entities=[MessageEntityBold(offset=0, length=11), MessageEntityBold(offset=22, length=3)], views=None, edit_date=None, post_author=None, grouped_id=None, restriction_reason=[]),
#         MessageService(id=1, to_id=PeerChannel(channel_id=1224462889), date=datetime.datetime(2020, 9, 11, 6, 59, 12, tzinfo=datetime.timezone.utc), action=MessageActionChannelCreate(title='yooooo'), out=False, mentioned=False, media_unread=False, silent=False, post=True, legacy=False, from_id=None, reply_to_msg_id=None),
#         Message(id=8, to_id=PeerUser(user_id=1116430935), date=datetime.datetime(2020, 9, 10, 22, 34, 32, tzinfo=datetime.timezone.utc), message='Hi You!. Press 📋 Menu to update', out=False, mentioned=False, media_unread=False, silent=False, post=False, from_scheduled=False, legacy=False, edit_hide=False, from_id=1264065847, fwd_from=None, via_bot_id=None, reply_to_msg_id=None, media=None, reply_markup=ReplyKeyboardMarkup(rows=[KeyboardButtonRow(buttons=[KeyboardButton(text='📋 Menu')])], resize=True, single_use=False, selective=False), entities=[MessageEntityBold(offset=0, length=7)], views=None, edit_date=None, post_author=None, grouped_id=None, restriction_reason=[]),
#         Message(id=2, to_id=PeerUser(user_id=1116430935), date=datetime.datetime(2020, 9, 10, 22, 34, 17, tzinfo=datetime.timezone.utc), message='http://t.me/robot_automatic_btc_v2_bot?start=1262608702', out=True, mentioned=False, media_unread=False, silent=False, post=False, from_scheduled=False, legacy=False, edit_hide=False, from_id=1116430935, fwd_from=None, via_bot_id=None, reply_to_msg_id=None, media=MessageMediaWebPage(webpage=WebPage(id=9170793120638774836, url='http://t.me/robot_automatic_btc_v2_bot?start=1262608702', display_url='t.me/robot_automatic_btc_v2_bot?start=1262608702', hash=0, type='telegram_bot', site_name='Telegram', title='Robot Automatic 🃏', description='Get free Bitcoin!!', photo=Photo(id=6249109336609630709, access_hash=2082125562235968269, file_reference=b'\x00_`-\x86\xa2\xdc\x1a!\x8f\xba\x8c\xfd*4\t\x13c\xba\xab\x87', date=datetime.datetime(2020, 6, 2, 13, 58, 50, tzinfo=datetime.timezone.utc), sizes=[PhotoSize(type='a', location=FileLocationToBeDeprecated(volume_id=500013600917, local_id=88473), w=160, h=160, size=6247), PhotoSize(type='b', location=FileLocationToBeDeprecated(volume_id=500013600917, local_id=88474), w=320, h=320, size=15319), PhotoSize(type='c', location=FileLocationToBeDeprecated(volume_id=500013600917, local_id=88475), w=640, h=640, size=38567)], dc_id=5, has_stickers=False), embed_url=None, embed_type=None, embed_width=None, embed_height=None, duration=None, author=None, document=None, documents=[], cached_page=None)), reply_markup=None, entities=[MessageEntityUrl(offset=0, length=55)], views=None, edit_date=None, post_author=None, grouped_id=None, restriction_reason=[])
#     ],
#     chats=[
#         Channel(id=1224462889, title='yooooo', photo=ChatPhotoEmpty(), date=datetime.datetime(2020, 9, 11, 6, 59, 43, tzinfo=datetime.timezone.utc), version=0, creator=False, left=False, broadcast=True, verified=False, megagroup=False, restricted=False, signatures=False, min=False, scam=False, has_link=False, has_geo=False, slowmode_enabled=False, access_hash=-5016983841942878644, username=None, restriction_reason=[], admin_rights=None, banned_rights=None, default_banned_rights=None, participants_count=2)
#     ],
#     users=[
#         User(id=777000, is_self=False, contact=False, mutual_contact=False, deleted=False, bot=False, bot_chat_history=False, bot_nochats=False, verified=True, restricted=False, min=False, bot_inline_geo=False, support=True, scam=False, access_hash=2556704287604659826, first_name='Telegram', last_name=None, username=None, phone='42777', photo=UserProfilePhoto(photo_id=3337190045231023, photo_small=FileLocationToBeDeprecated(volume_id=107738948, local_id=13226), photo_big=FileLocationToBeDeprecated(volume_id=107738948, local_id=13228), dc_id=1), status=UserStatusOffline(was_online=datetime.datetime(2019, 8, 13, 0, 13, 44, tzinfo=datetime.timezone.utc)), bot_info_version=None, restriction_reason=[], bot_inline_placeholder=None, lang_code=None),
#         User(id=1264065847, is_self=False, contact=False, mutual_contact=False, deleted=False, bot=True, bot_chat_history=False, bot_nochats=False, verified=False, restricted=False, min=False, bot_inline_geo=False, support=False, scam=False, access_hash=-1977745644042916041, first_name='Robot Automatic 🃏', last_name=None, username='robot_automatic_btc_v2_bot', phone=None, photo=UserProfilePhoto(photo_id=6249109336609630709, photo_small=FileLocationToBeDeprecated(volume_id=500013600917, local_id=88473), photo_big=FileLocationToBeDeprecated(volume_id=500013600917, local_id=88475), dc_id=5), status=None, bot_info_version=4, restriction_reason=[], bot_inline_placeholder=None, lang_code=None),
#         User(id=1116430935, is_self=True, contact=False, mutual_contact=False, deleted=False, bot=False, bot_chat_history=False, bot_nochats=False, verified=False, restricted=False, min=False, bot_inline_geo=False, support=False, scam=False, access_hash=-6009656644516679628, first_name='Ycyc', last_name='Ycu', username=None, phone='12016032037', photo=None, status=UserStatusOffline(was_online=datetime.datetime(2020, 9, 11, 7, 1, 15, tzinfo=datetime.timezone.utc)), bot_info_version=None, restriction_reason=[], bot_inline_placeholder=None, lang_code=None)
#     ]
# )


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

