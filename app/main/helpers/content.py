import yaml
import inflection
import re
import os


class ContentLoader(object):

    def __init__(self, manifest, content_directory):

        with open(manifest, "r") as file:
            section_order = yaml.load(file)

        self._directory = content_directory
        self._question_cache = {}
        self.sections = [
            self.__populate_section__(s) for s in section_order
        ]

    def get_section(self, requested_section):

        for section in self.sections:
            if section["id"] == requested_section:
                return section

    def get_question(self, question):

        if question not in self._question_cache:

            question_file = self._directory + question + ".yml"

            if not os.path.isfile(question_file):
                self._question_cache[question] = {}
                return {}

            with open(question_file, "r") as file:
                question_content = yaml.load(file)

            question_content["id"] = question

            # wrong way to do it? question should be shown by default.
            question_content["depends_on_lots"] = (
                self.__get_dependent_lots__(question_content["dependsOnLots"])
            ) if "dependsOnLots" in question_content else (
                ["saas", "paas", "iaas", "scs"]
            )

            self._question_cache[question] = question_content

        return self._question_cache[question]

    def __populate_section__(self, section):
        section["questions"] = [
            self.get_question(q) for q in section["questions"]
        ]
        all_dependencies = [
            q["depends_on_lots"] for q in section["questions"]
        ]
        section["depends_on_lots"] = [
            y for x in all_dependencies for y in x  # flatten array
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
