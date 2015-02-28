import os.path
import time
import shutil


class Validate():

    def __init__(self, posted_data):
        self.posted_data = posted_data

    def test(self, rule):
        if not hasattr(self, rule):
            raise Exception("Validation rule " + rule + " not found")
        return getattr(self, rule)()

    def __file_has_contents(self):

        first_file = self.posted_data[0]
        return len(first_file.read())

    def save_file(self):

        first_file = self.posted_data[0]

        if not self.__file_has_contents():
            return False

        tmp = "/Users/chs/gdsworkspace/digitalmarketplace-admin-frontend/temp/"

        file_name, file_extension = os.path.splitext(first_file.filename)
        destination = os.path.join(
            tmp, file_name + file_extension
        )

        if os.path.isfile(destination):
            now = time.strftime('--%Y-%m-%d-%H-%M-%S')
            old_version = os.path.join(tmp, file_name + now + file_extension)
            shutil.move(destination, old_version)

        first_file.save(destination)
        return True
