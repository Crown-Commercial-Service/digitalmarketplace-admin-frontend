import os.path
import time
import shutil


class Validate():

    def __init__(self, content, service, posted_data):
        self.content = content
        self.service = service
        self.posted_data = posted_data

    @property
    def errors(self):
        errors = {}
        for question_id in self.posted_data:
            question_errors = self.question_errors(question_id)
            if question_errors:
                errors[question_id] = question_errors

        return errors

    def question_errors(self, question_id):
        question = self.posted_data[question_id]
        question_content = self.content.get_question(question_id)

        if not self.test(question, "answer_required"):
            if "optional" in question_content:
                return
            # File has previously been uploaded
            if question_id in self.service:
                return

        for rule in question_content["validations"]:
            if not self.test(question, rule["name"]):
                return rule["message"]

        # TODO We can't update file URLs until we have the write API,
        # so uploaded file must have the same extension as the
        # current one for now
        current_extension = get_extension(self.service[question_id])
        if get_extension(question.filename) != current_extension:
            return u"Uploaded file format should be: %s" % current_extension

    def test(self, question, rule):
        if not hasattr(self, rule):
            raise ValueError("Validation rule " + rule + " not found")
        return getattr(self, rule)(question)

    def answer_required(self, question):
        not_empty = len(question.read(1)) > 0
        question.seek(0)
        return not_empty

    def file_can_be_saved(self, question):
        tmp = "./temp/"

        file_name, file_extension = os.path.splitext(question.filename)
        destination = os.path.join(
            tmp, file_name + file_extension
        )

        if os.path.isfile(destination):
            now = time.strftime('--%Y-%m-%d-%H-%M-%S')
            old_version = os.path.join(tmp, file_name + now + file_extension)
            shutil.move(destination, old_version)

        question.save(destination)
        return True

    def file_is_less_than_5mb(self, question):
        size_limit = 5400000
        below_size_limit = len(question.read(size_limit)) < size_limit
        question.seek(0)

        return below_size_limit

    def file_is_open_document_format(self, question):

        return get_extension(question.filename) in [
            ".pdf", ".pda", ".odt", ".ods", ".odp"
        ]


def get_extension(filename):
    file_name, file_extension = os.path.splitext(filename)
    return file_extension.lower()
