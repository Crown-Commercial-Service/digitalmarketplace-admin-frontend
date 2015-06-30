
class User(object):
    def __init__(self, user_id, email_address):
        self.id = user_id
        self.email_address = email_address

    @staticmethod
    def is_authenticated():
        return True

    @staticmethod
    def is_active():
        return True

    @staticmethod
    def is_anonymous():
        return False

    def get_id(self):
        try:
            return unicode(self.id)
        except NameError:
            return str(self.id)

    @staticmethod
    def from_json(user_json):
        user = user_json['users']
        return User(
            user_id=user['id'],
            email_address=user['emailAddress'])
