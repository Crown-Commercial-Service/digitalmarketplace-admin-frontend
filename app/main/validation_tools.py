import os


class Validations():

    temp = "/Users/chs/gdsworkspace/digitalmarketplace-admin-frontend/temp/"

    def upload_to_S3(self, question_id, posted_data):
        first_file = posted_data[0]
        file_size = len(first_file.read())
        if file_size < 1:
            return False
        first_file.save(os.path.join(self.temp, first_file.filename))
        return True
