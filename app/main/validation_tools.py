import os.path
import time
import shutil


class Validations():

    def file_has_contents(self, file):
        return len(file.read())

    def save_file(self, question_id, posted_data):

        first_file = posted_data[0]

        if not self.file_has_contents(first_file):
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
