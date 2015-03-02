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

    def answer_required(self):

        first_file = self.posted_data[0]
        first_file.seek(0)
        return len(first_file.read()) > 0

    def file_can_be_saved(self):

        if not self.answer_required():
            return False

        first_file = self.posted_data[0]

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

    def file_is_less_than_5mb(self):

        first_file = self.posted_data[0]
        first_file.seek(0)

        return len(first_file.read()) < 5400000

    def file_is_open_document_format(self):

        first_file = self.posted_data[0]
        file_name, file_extension = os.path.splitext(first_file.filename)

        return file_extension.lower() in [".pdf", ".pda", ".odt", ".ods", ".odp"];
