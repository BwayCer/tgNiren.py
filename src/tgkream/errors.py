#!/usr/bin/env python3


class PickPhoneMoreTimes(Exception): pass
class WhoIsPapa(Exception): pass
class UserNotAuthorized(Exception): pass
class errMsg():
    PickPhoneMoreTimes = 'Loop more times at pick phone.'
    WhoIsPapa = 'Don\'t know Papa he is'
    SessionFileNotExistsTemplate = 'The session file of "{}" NiUser is not exists.'
    UserNotAuthorizedTemplate = 'The "{}" NiUser is not authorized.'

