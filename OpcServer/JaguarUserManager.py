from asyncua.server.user_managers import UserManager


class JaguarUserManager(UserManager):

    def __init__(self):
        self._username = ''
        self._password = ''

    def get_user(self, iserver, username=None, password=None, certificate=None):
        print('get_User_call')
        print(username, password)
        return True
