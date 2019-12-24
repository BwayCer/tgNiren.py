#!/usr/bin/env python3


import typing
import os
import datetime
import json
import asyncio
import utils.novice
import utils.json
from tgkream.tgTool import TgBaseTool, telethon


def run(args: list, _dirpy: str, _dirname: str):
    asyncio.run(asyncRun(args, _dirpy, _dirname))

# "{\"mainGroup\":\"propagonda\",\"forwardPeerList\":[\"hk80808080\",\"@dd99999999\",\"https://t.me/abchi777\",\"tes_b\",\"maru8001\",\"lnnL1s\"],\"url\":\"pika.jpg\",\"msg\":\"hi\"}"
# "{\"forwardPeerList\":[\"hk80808080\",\"dd99999999\",\"bb99999999\"],\"url\":\"pika.jpg\",\"msg\":\"hi\"}"
async def asyncRun(args: list, _dirpy: str, _dirname: str):
    data = json.loads(args[1])

    _env = utils.json.loadYml(_dirname + '/env.yml')

    forwardPeers = data['forwardPeerList']
    url = data['url']
    msg = data['msg']

    mainGroup = _env['peers']['adChannle']
    tgTool = TgBaseTool(
        _env['apiId'],
        _env['apiHash'],
        sessionDirPath = _dirname + '/_tgSession',
        clientCount = 3,
        papaPhone = _env['papaPhoneNumber']
    )
    await tgTool.init()

    messageId = await _sendFile(tgTool, mainGroup, url, msg)
    # messageId = 10

    if messageId == -1:
        raise Exception('Use Papa send file fail. (url: {}, msg: {})'.format(url, msg))

    finalPeers = _filterGuy(tgTool, forwardPeers)
    finalPeersLength = len(finalPeers)
    idx = -1
    async for client in tgTool.iterPickClient(-1, 3):
        idx += 1
        if finalPeersLength <= idx:
            break

        forwardPeer = finalPeers[idx]
        # TODO 不太會被封 需再測試才能確定 try cache 語句是否有錯誤
        try:
            await tgTool.joinGroup(client, forwardPeer)
            await client(telethon.functions.messages.ForwardMessagesRequest(
                from_peer = mainGroup,
                id = [messageId],
                to_peer = forwardPeer,
                random_id = [tgTool.getRandId()]
            ))
        except telethon.errors.MessageIdInvalidError as err:
            print('MessageIdInvalidError: {}'.format(err))
            raise err
        except telethon.errors.FloodWaitError as err:
            waitTimeSec = err.seconds
            print("FloodWaitError: wait {} seconds.".format(waitTimeSec))
            myInfo = await client.get_me()
            maturityDate = datetime.datetime.now() \
                + datetime.timedelta(seconds = waitTimeSec)
            tgTool.chanDataNiUsers.pushBandData(myInfo.phone, maturityDate)
            await tgTool.reinit()
        except telethon.errors.ChatWriteForbiddenError as err:
            # You can't write in this chat
            print('ChatWriteForbiddenError: {}'.format(err))
            tgTool.chanData.pushGuy(
                await client.get_entity(forwardPeer),
                err
            )
        except Exception as err:
            print('{} Error: {} (target group: {})'.format(type(err), err, forwardPeer))


async def _sendFile(tgTool: TgBaseTool, group: str, url: str, msg: str = '') -> int:
    async with tgTool.usePapaClient() as client:
        inputFile = await client.upload_file(url)
        # # telethon.tl.custom.inputsizedfile.InputSizedFile
        # InputFile(id=1998985368889578973, parts=2, name='togepi.jpg', md5_checksum='c3a9295496628d2580a10c84f2670004')

        rtnUpdates = await client(telethon.functions.messages.SendMediaRequest(
            peer = group,
            media = telethon.types.InputMediaUploadedPhoto(
                file = inputFile,
                ttl_seconds = None
            ),
            message = msg
        ))
        # # telethon.tl.types.Updates
        # Updates(
        #     updates=[
        #         UpdateMessageID(
        #             id=9,
        #             random_id=-4446444845156303398
        #         ),
        #         UpdateReadChannelInbox(
        #             channel_id=1403722009,
        #             max_id=9,
        #             still_unread_count=0,
        #             pts=11,
        #             folder_id=None
        #         ),
        #         UpdateNewChannelMessage(
        #             message=Message(
        #                 id=9,
        #                 to_id=PeerChannel(
        #                     channel_id=1403722009
        #                 ),
        #                 date=datetime.datetime(2019, 12, 15, 7, 51, 48, tzinfo=datetime.timezone.utc),
        #                 message='私はトゲピーです',
        #                 out=True,
        #                 mentioned=False,
        #                 media_unread=False,
        #                 silent=False,
        #                 post=True,
        #                 from_scheduled=False,
        #                 legacy=False,
        #                 edit_hide=False,
        #                 from_id=None,
        #                 fwd_from=None,
        #                 via_bot_id=None,
        #                 reply_to_msg_id=None,
        #                 media=MessageMediaPhoto(
        #                     photo=Photo(
        #                         id=5166103319691765823,
        #                         access_hash=718304123442586659,
        #                         file_reference=b'\x04S\xab\x19\x19\x00\x00\x00\t]\xf5\xe6\x14bfD$\x06=\x91\xb8\xfc\xfe\x92\xd1\x1c?\x02\xfc',
        #                         date=datetime.datetime(2019, 12, 15, 7, 51, 48, tzinfo=datetime.timezone.utc),
        #                         sizes=[
        #                             PhotoStrippedSize(
        #                                 type='i',
        #                                 bytes=b'\x01((\xd9\xa4\x0c\x0fCJj\x18\x8f\xcb\x8e\xe3\x8a\x99;\r"M\xdc\xf1N\xcdG\xc0\xe3\xd6\x82H\x1djT\x82\xc4\x94P:sEh!\xaev\xa15\nmR\x06\xe1\x93\xebRN\xa5\xa1`\xbdj\x8d\xbb$\xb2\x02I\x03\xb8\xf7\xa4\xd5\xca\x89;F\xedr\x92\x97\xc2 \xfb\xbe\xbc\x1f\xf1\xa7F\x8c.d\x90\x9c\xab\x81\x81\xe9\x8ap\x0b\x9c\x04<\xf4\xc9\xa7.\xc1&\xd5\xceGoJ\x84\x82\xe4\xb4QEhHUy-#w\xdf\x8d\xad\xd7#\xbd\x14P\x02\xad\xb9\x07qs\x93\xe9K\x1d\xb8BIb\xc4\xd1E+!\xdd\x93QE\x14\xc4\x7f'
        #                             ),
        #                             PhotoSize(
        #                                 type='m',
        #                                 location=FileLocationToBeDeprecated(
        #                                     volume_id=107734911,
        #                                     local_id=115595
        #                                 ),
        #                                 w=320,
        #                                 h=317,
        #                                 size=13051
        #                             ),
        #                             PhotoSize(
        #                                 type='x',
        #                                 location=FileLocationToBeDeprecated(
        #                                     volume_id=107734911,
        #                                     local_id=115596
        #                                 ),
        #                                 w=500,
        #                                 h=496,
        #                                 size=24983
        #                             ),
        #                         ],
        #                         dc_id=1,
        #                         has_stickers=False
        #                     ),
        #                     ttl_seconds=None
        #                 ),
        #                 reply_markup=None,
        #                 entities=[],
        #                 views=1,
        #                 edit_date=None,
        #                 post_author=None,
        #                 grouped_id=None,
        #                 restriction_reason=[]
        #             ),
        #             pts=11,
        #             pts_count=1
        #         ),
        #     ],
        #     users=[],
        #     chats=[
        #         Channel(
        #             id=1403722009,
        #             title='Mars Propaganda',
        #             photo=ChatPhoto(
        #                 photo_small=FileLocationToBeDeprecated(
        #                     volume_id=107735363,
        #                     local_id=109979
        #                 ),
        #                 photo_big=FileLocationToBeDeprecated(
        #                     volume_id=107735363,
        #                     local_id=109981
        #                 ),
        #                 dc_id=1
        #             ),
        #             date=datetime.datetime(2019, 12, 6, 6, 43, 20, tzinfo=datetime.timezone.utc),
        #             version=0,
        #             creator=True,
        #             left=False,
        #             broadcast=True,
        #             verified=False,
        #             megagroup=False,
        #             restricted=False,
        #             signatures=False,
        #             min=False,
        #             scam=False,
        #             has_link=False,
        #             has_geo=False,
        #             slowmode_enabled=False,
        #             access_hash=-5655335786021561219,
        #             username='propagonda',
        #             restriction_reason=[],
        #             admin_rights=None,
        #             banned_rights=None,
        #             default_banned_rights=None,
        #             participants_count=None
        #         ),
        #     ],
        #     date=datetime.datetime(2019, 12, 15, 7, 51, 47, tzinfo=datetime.timezone.utc),
        #     seq=0
        # )

        messageId = -1
        for update in rtnUpdates.updates:
            if type(update) == telethon.types.UpdateMessageID:
                messageId = update.id
                break

    return messageId

def _filterGuy(tgTool: TgBaseTool, mainList: typing.List[str]) -> typing.List[str]:
    blackGuyList = tgTool.chanData.get('.blackGuy.list')
    newList = []
    for peer in mainList:
        if utils.novice.indexOf(blackGuyList, peer) == -1:
            newList.append(peer)
    return newList

