#!/usr/bin/env python3


import typing
import asyncio
import utils.novice as novice
import utils.json
from tgkream.tgSimple import telethon, TgDefaultInit, TgSimple


def run(args: list, _dirpy: str, _dirname: str):
    asyncio.run(asyncRun(args, _dirpy, _dirname), debug = True)

async def asyncRun(args: list, _dirpy: str, _dirname: str):
    if len(args) < 5:
        raise ValueError('Usage: <phoneNumber> <groupPeer> <offsetDays> <jsonFilePath>')

    phoneNumber = args[1]
    groupPeer = args[2]
    offsetDays = float(args[3])
    jsonFilePath = args[4]

    tgTool = TgDefaultInit(TgSimple)

    print('-> 登入用戶')
    client = await tgTool.login(phoneNumber)
    if client == None:
        print('--> 未登入此用戶')

    myInfo = await client.get_me()
    print('--> I\'m {} {} ({}) and my phone is +{}.'.format(
        str(myInfo.first_name),
        str(myInfo.last_name),
        str(myInfo.username),
        myInfo.phone,
    ))

    groupEntity = await client.get_entity(groupPeer)
    if type(groupEntity) != telethon.types.Channel:
        print('-> 非群組聊天室')

    _, isPrivate = telethon.utils.parse_username(groupPeer)
    if isPrivate:
        print('-> 加入聊天室')
        try:
            await tgTool.joinGroup(client, groupPeer)
        except telethon.errors.UserAlreadyParticipantError as err:
            # 已經是聊天的參與者。 (私有聊天室)
            pass
        except Exception as err:
            errType = type(err)
            if telethon.errors.ChannelsTooMuchError == errType:
                print('您加入了太多的頻道/超級群組。')
            elif telethon.errors.ChannelInvalidError == errType:
                print('無效的頻道對象。')
            elif telethon.errors.ChannelPrivateError == errType:
                print('指定的對象為私人頻道/超級群組。另一個原因可能是您被禁止了。')
            elif telethon.errors.InviteHashEmptyError == errType:
                print('邀請連結丟失。 (私有聊天室)')
            elif telethon.errors.InviteHashExpiredError == errType:
                print('聊天室已過期。 (私有聊天室)')
            elif telethon.errors.InviteHashInvalidError == errType:
                print('無效的邀請連結。 (私有聊天室)')
            elif telethon.errors.SessionPasswordNeededError == errType:
                print('啟用了兩步驗證，並且需要密碼。 (私有聊天室)(登入錯誤?)')
            elif telethon.errors.UsersTooMuchError == errType:
                print('超過了最大用戶數 (ex: 創建聊天)。 (私有聊天室)')
            else:
                print('{} Error: {} (from: {})'.format(
                    errType, err, 'tgTool.joinGroup()'
                ))
            raise err

    print('-> 取得活躍帳戶名單')
    try:
        users = await _getActiveParticipants(client, groupPeer, offsetDays)
        userNames = []
        for user in users:
            username = user.username
            if username == None:
                continue
            userNames.append(username)
    except Exception as err:
        errType = type(err)
        if telethon.errors.ChannelInvalidError == errType:
            print('無效的頻道對象。')
        elif telethon.errors.ChannelPrivateError == errType:
            print('指定的對象為私人頻道/超級群組。另一個原因可能是您被禁止了。')
        elif telethon.errors.ChatAdminRequiredError == errType:
            print('您沒有執行此操作的權限。')
        elif telethon.errors.InputConstructorInvalidError == errType:
            print('提供的構造函數無效。 (*程式錯誤)')
        elif telethon.errors.TimeoutError == errType:
            print('從工作程序中獲取數據時發生超時。 (*程式錯誤)')
        else:
            print('{} Error: {} (from: {})'.format(
                errType, err, 'tgTool.getParticipants()'
            ))
        raise err

    print(f'--> 從 {len(users)} 位活躍用戶中提取出 {len(userNames)} 位可搜尋的用戶名單')
    utils.json.dump(userNames, jsonFilePath)


async def _getActiveParticipants(
        client: telethon.TelegramClient,
        groupPeer: str,
        offsetDays: float = 1,
        amount: int = 0) -> typing.List[telethon.types.User]:
    if offsetDays < 1:
        raise Exception(f'時間偏移量須為大於 1 的正數。')
    if amount < 0:
        raise Exception(f'取得用戶總量須為正整數。')

    theDt = novice.dateUtcNowOffset(days = -1 * offsetDays)

    # NOTE: 關於 `GetHistoryRequest()` 方法
    # https://core.telegram.org/method/messages.getHistory
    # https://tl.telethon.dev/methods/messages/get_history.html
    # 1. 當對象為用戶時，沒有訊息?! (2020.11.23 紀錄)
    # 關於參數值：
    #   1. `offset_id`, `add_offset` 用於選取在特定訊息前或後的訊息，不使用則傳入 `0`。
    #   2. `offset_date`, `max_id`, `min_id` 用於選取在特定範圍內的訊息
    #      注意！ 感覺是先使用 `offset_date` 和 `limit` 先選定範圍，
    #      再篩選符合的 `max_id`, `min_id` 的項目，
    #      所以當 `offset_date` 不變的情況下，取得訊息的數量只會越來越少。
    #   3. `offset_date` 若傳入 `0|None`，則預設為當前時間。
    #   4. Telegram 時間為 UTC 時間。
    # 關於回傳值：
    #   https://core.telegram.org/constructor/messages.channelMessages
    #   1. `count` 為該聊天室紀錄於服務端的總訊息比數。
    #      (但可能不完全紀錄於服務端 ?! (官方說的))
    #   2. 回傳的訊息是依時間倒序排序的。
    #   3. `chats`, `users` 中包含 `messages` 所提到的對象 (ex: 轉傳的訊息對象也在裡面)
    #   4. `limit` 最多為 100 則。 (2020.11.23 紀錄)

    result = await client(telethon.functions.messages.GetHistoryRequest(
        peer = groupPeer,
        offset_id = 0,
        offset_date = theDt,
        add_offset = 0,
        limit = 1,
        max_id = 0,
        min_id = 0,
        hash = 0
    ))
    oldMsgId = result.messages[0].id if len(result.messages) > 0 else 1

    isBleak = False
    currDate = None
    currMinMsgId = 0
    userList = []
    activeUserList = []
    while True:
        result = await client(telethon.functions.messages.GetHistoryRequest(
            peer = groupPeer,
            offset_id = 0,
            offset_date = currDate,
            add_offset = 0,
            limit = 100,
            max_id = currMinMsgId,
            min_id = oldMsgId,
            hash = 0
        ))
        print(f'pts: {result.pts}, count: {result.count}, messages: {len(result.messages)}, chats: {len(result.chats)}, users: {len(result.users)}')

        messagesLength = len(result.messages)
        if messagesLength == 0:
            break
        print(f'  {result.messages[0].id}({result.messages[0].date}) ~ {result.messages[messagesLength - 1].id}({result.messages[messagesLength - 1].date})')

        for user in result.users:
            # 排除 自己, 已刪除帳號, 機器人
            if user.is_self or user.deleted or user.bot:
                continue

            # 過濾已抓取的
            if user.id in userList:
                continue

            userList.append(user.id)
            activeUserList.append(user)

            if amount != 0 and len(activeUserList) >= amount:
                isBleak = True
                break
        print(f'  get {len(result.users)} users -> {len(activeUserList)}')

        if isBleak:
            break

        currDate = result.messages[messagesLength - 1].date
        currMinMsgId = result.messages[messagesLength - 1].id

    return activeUserList

