import yaml
import inflection
import re


class Content_loader():

    def __init__(self, manifest, content_directory):

        section_order = yaml.load(open(manifest, "r"))

        self.directory = content_directory
        self.__question_cache__ = {}
        self.sections = [
            self.__populate_section__(s) for s in section_order
        ]

    def get_section(self, requested_section):

        for section in self.sections:
            if section["id"] == requested_section:
                return section

    def get_question(self, question):

        if question not in self.__question_cache__:

            question_content = yaml.load(
                open(str(self.directory) + str(question) + ".yml", "r")
            )

            question_content["id"] = question

            # wrong way to do it? question should be shown by default.
            question_content["dependsOnLots"] = (
                self.__get_dependent_lots__(question_content["dependsOnLots"])
            ) if "dependsOnLots" in question_content else (
                ["saas", "paas", "iaas", "scs"]
            )

            self.__question_cache__[question] = question_content

        return self.__question_cache__[question]

    def __populate_section__(self, section):
        section["questions"] = [
            self.get_question(q) for q in section["questions"]
        ]
        section["id"] = self.__make_id__(section["name"])
        return section

    def __make_id__(self, name):
        return inflection.underscore(
            re.sub("\s", "_", name)
        )

    def __get_dependent_lots__(self, dependent_lots_as_string):
        return [
            x.strip() for x in dependent_lots_as_string.lower().split(",")
        ]
