import re

class Presenters(object):

    def __init__(self):
        return None

    def present(self, value, question_content):
        if "type" in question_content:
            field_type = question_content["type"]
        else:
            return value

        if hasattr(self, "_" + field_type):
            return getattr(self, "_" + field_type)(value)
        else:
            return value

    def _service_id(self, value):
        return re.findall(
            "....", str(value)
        )

    def _upload(self, value):
        return {
            "url": value or "",
            "filename": value.split("/")[-1] or ""
        }
