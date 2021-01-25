#!/usr/bin/env python3


class PickPhoneMoreTimes(Exception): pass
class WhoIsPapa(Exception): pass
class UserNotAuthorized(Exception): pass
class errMsg():
    PickPhoneMoreTimes = 'Loop more times at pick phone.'
    WhoIsPapa = 'Don\'t know Papa he is'
    SessionFileNotExistsTemplate = 'The session file of "{}" NiUser is not exists.'
    UserNotAuthorizedTemplate = 'The "{}" NiUser is not authorized.'


class knownError():
    def has(methodName: str, err: Exception) -> bool:
        if not hasattr(knownError, methodName):
            return False

        return err.__class__.__name__ in getattr(knownError, methodName)

    def getMsg(methodName: str, err: Exception) -> str:
        if not knownError.has(methodName, err):
            return ''

        errTypeName = err.__class__.__name__
        info = getattr(knownError, methodName)
        msg = info[errTypeName]

        return msg if msg != '' else knownError.allMsg[errTypeName]

    joinGroupMethod = {
        'ChannelsTooMuchError': '',
        'ChannelInvalidError': '',
        'ChannelPrivateError': '',
        'InviteHashEmptyError': '邀請連結丟失。 (私有聊天室)',
        'InviteHashExpiredError': '邀請連結已過期。 (私有聊天室)',
        'InviteHashInvalidError': '無效的邀請連結。 (私有聊天室)',
        'SessionPasswordNeededError': '啟用了兩步驗證，並且需要密碼。 (私有聊天室)(登入錯誤?)',
        'UsersTooMuchError': '超過了最大用戶數 (ex: 創建聊天)。 (私有聊天室)',
        'UserAlreadyParticipantError': '已經是聊天的參與者。 (私有聊天室)',
        # 只有在 https://core.telegram.org/method/messages.importChatInvite 的錯誤
        # 400 MSG_ID_INVALID
        # 400 PEER_ID_INVALID
        # 只有在 https://core.telegram.org/method/channels.JoinChannel 的錯誤
        # 400 INVITE_HASH_EMPTY
        # 400 INVITE_HASH_EXPIRED
        # 400 INVITE_HASH_INVALID
        # 400 MSG_ID_INVALID
        # 400 PEER_ID_INVALID
        # 400 USERS_TOO_MUCH
        # 400 USER_ALREADY_PARTICIPANT
        # 400 USER_CHANNELS_TOO_MUCH
    }

    SendMessageRequest = {
        'BotDomainInvalidError': '無效的機器人網域。',
        'ButtonDataInvalidError': '無效的按鈕數據。',
        'ButtonTypeInvalidError': '無效的按鈕類型。',
        'ButtonUrlInvalidError': '無效的按鈕網址。',
        'ChannelInvalidError': '',
        'ChannelPrivateError': '',
        'ChatAdminRequiredError': '',
        'ChatIdInvalidError': '',
        'ChatRestrictedError': '',
        'ChatWriteForbiddenError': '',
        'EntityMentionUserInvalidError': '無效的提及對象。',
        'InputUserDeactivatedError': '您指定的用戶已被刪除。',
        'MessageEmptyError': '無法發送空白訊息。',
        'MessageTooLongError': '訊息太長。 (當前的最大長度為 4096 個 UTF-8 字符)',
        'MsgIdInvalidError': '無效的 reply_to_msg_id。',
        'PeerIdInvalidError': '',
        'ReplyMarkupInvalidError': '無效的回覆標記。',
        'ScheduleBotNotAllowedError':  '禁止機器人安排消息。',
        'ScheduleDateTooLateError': '您安排的日期距離太遙遠。 (最近的已知限制為 1 年零幾個小時)',
        'ScheduleTooMuchError': '您無法在此聊天中安排更多消息。 (最近一次聊天限制為 100 個)',
        'UserBannedInChannelError': '',
        'UserIsBlockedError': '您已被用戶封鎖。',
        'UserIsBotError': '機器人無法發送消息給其他機器人。',
        'YouBlockedUserError': '您已封鎖了該用戶。',
        # 只有在 https://core.telegram.org/method/messages.sendMessage 的錯誤
        # 401 AUTH_KEY_PERM_EMPTY The temporary auth key must be binded to the permanent auth key to use these methods.
        # 400 BOT_INVALID This is not a valid bot
        # 400 ENCRYPTION_DECLINED The secret chat was declined
        # 400 FROM_MESSAGE_BOT_DISABLED Bots can't use fromMessage min constructors
        # 400 PINNED_DIALOGS_TOO_MUCH Too many pinned dialogs
        # 420 SLOWMODE_WAIT_X Slowmode is enabled in this chat: you must wait for the specified number of seconds before sending another message to the chat.
        # 只有在 https://tl.telethon.dev/methods/messages/send_message.html 的錯誤
        'AuthKeyDuplicatedError': '',
        'EntitiesTooLongError': '無法發送如此大數據的實體標籤 (例如內聯文字網址)。',
        'PollOptionInvalidError': '投票選項使用了無效數據。 (數據可能太長)',
        'RandomIdDuplicateError': '您提供了已經使用的隨機 ID。',
        'ReplyMarkupTooLongError': 'The data embedded in the reply markup buttons was too much.',
        'ScheduleStatusPrivateError': 'You cannot schedule a message until the person comes online if their privacy does not show this information.',
        'TimeoutError': '',
    }

    GetDialogsRequest = {
        'InputConstructorInvalidError': '提供的構造函數無效。',
        'OffsetPeerIdInvalidError': '提供的偏移對等點無效。',
        # 只有在 https://core.telegram.org/method/messages.getDialogs 的錯誤
        # 400 FOLDER_ID_INVALID   Invalid folder ID
        # 只有在 https://tl.telethon.dev/methods/messages/get_dialogs.html 的錯誤
        'SessionPasswordNeededError': '',
        'TimeoutError': '',
    }

    GetHistoryRequest = {
        # 必須將臨時身份驗證密鑰綁定到永久身份驗證密鑰，才能使用這些方法。
        # 該方法不適用於臨時授權密鑰，未綁定到永久授權密鑰。
        'AuthKeyPermEmptyError': 'The temporary auth key must be binded to the permanent auth key to use these methods.',
        'ChannelInvalidError': '',
        'ChannelPrivateError': '',
        'ChatIdInvalidError': '',
        'PeerIdInvalidError': '',
        # 只有在 https://core.telegram.org/method/messages.getHistory 的錯誤
        # 400 CONNECTION_DEVICE_MODEL_EMPTY   設備型號為空
        # 400 MSG_ID_INVALID  提供的消息ID無效
        # 只有在 https://tl.telethon.dev/methods/messages/get_history.html 的錯誤
        'AuthKeyDuplicatedError': '',
        'TimeoutError': '',
    }

    InviteToChannelRequest = {
        'BotGroupsBlockedError': '',
        'BotsTooMuchError': '',
        'ChannelInvalidError': '',
        'ChannelPrivateError': '',
        'ChatAdminRequiredError': '',
        'ChatInvalidError': '',
        'ChatWriteForbiddenError': '',
        'InputUserDeactivatedError': '',
        'UserBannedInChannelError': '',
        'UserBlockedError': '',
        'UserBotError': '',
        'UserChannelsTooMuchError': '',
        'UserIdInvalidError': '',
        'UserKickedError': '',
        'UserNotMutualContactError': '',
        'UserPrivacyRestrictedError': '',
        'UsersTooMuchError': '',
        # 只有在 https://core.telegram.org/method/channels.inviteToChannel 的錯誤
        # 400 MSG_ID_INVALID  Invalid message ID provided
    }

    allMsg = {
        # 授權密鑰（會話文件）已同時在兩個不同的IP地址下使用，不能再使用。單獨使用同一會話，或使用不同的會話。
        'AuthKeyDuplicatedError': 'The authorization key (session file) was used under two different IP addresses simultaneously, and can no longer be used. Use the same session exclusively, or use different sessions.',
        'AuthKeyPermEmptyError': 'The temporary auth key must be binded to the permanent auth key to use these methods.',
        'BotGroupsBlockedError': '此機器人不能被加到群組中。',
        'BotsTooMuchError': '過多的機器人在聊天/頻道中。',
        'ChannelInvalidError': '無效的頻道對象。',
        'ChannelPrivateError': '您無法加入私人的頻道/超級群組。另一個原因可能是您被禁止了。',
        'ChannelsTooMuchError': '您加入了太多的頻道/超級群組。',
        'ChatAdminRequiredError': '您沒有執行此操作的權限。',
        'ChatIdInvalidError': '無效的 Chat ID 對象。',
        'ChatInvalidError': '無效的聊天對象。',
        'ChatRestrictedError': '您在此此聊天中是受限制的而無法傳送訊息。',
        'ChatWriteForbiddenError': '您無法在此聊天中發送訊息。',
        'InputUserDeactivatedError': '指定的用戶已被刪除。',
        'InviteHashEmptyError': '邀請連結丟失。',
        'InviteHashExpiredError': '邀請連結已過期。',
        'InviteHashInvalidError': '無效的邀請連結。',
        'PeerIdInvalidError': '無效的 Peer ID 對象。',
        'SessionPasswordNeededError': '啟用了兩步驗證，並且需要密碼。',
        'TimeoutError': '請求超時。', # python 原生錯誤類型
        'UserAlreadyParticipantError': '已經是聊天的參與者。',
        'UserBannedInChannelError': '您被禁止在超級群組/頻道中發送消息。',
        'UserBlockedError': '被用戶拒絕。', # 黑名單
        'UserBotError': '機器人只能是頻道中的管理員。',
        'UserChannelsTooMuchError': '您嘗試加入的用戶之一已經加入太多的超級群組/頻道。',
        'UserIdInvalidError': '無效的用戶 ID 對象。',
        'UserKickedError': '此用戶從超級群組/頻道中被踢出。',
        'UserNotMutualContactError': '此用戶與您不是相互的聯絡人。',
        'UserPrivacyRestrictedError': '用戶的隱私設置不允許您執行此操作。',
        'UsersTooMuchError': '超過了最大用戶數 (ex: 創建聊天)。',
    }

