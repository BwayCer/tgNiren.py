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
        'BotGroupsBlockedError': '此機器人不能被加到群組中。',
        'BotsTooMuchError': '過多的機器人在聊天/頻道中。',
        'ChannelInvalidError': '無效的頻道對象。',
        'ChannelPrivateError': '您無法加入私人的頻道/超級群組。另一個原因可能是您被禁止了。',
        'ChannelsTooMuchError': '您加入了太多的頻道/超級群組。',
        'ChatAdminRequiredError': '您沒有執行此操作的權限。',
        'ChatInvalidError': '無效的聊天對象。',
        'ChatWriteForbiddenError': '您無法在此聊天中發送訊息。',
        'InputUserDeactivatedError': '指定的用戶已被刪除。',
        'InviteHashEmptyError': '邀請連結丟失。',
        'InviteHashExpiredError': '邀請連結已過期。',
        'InviteHashInvalidError': '無效的邀請連結。',
        'SessionPasswordNeededError': '啟用了兩步驗證，並且需要密碼。',
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

