import difflib
from flask import Markup


class BaseDiffTool(object):
    """Creates a line-by-line diff from two lists of items"""

    def __init__(self, revision_1, revision_2):
        self.revision_1 = revision_1
        self.revision_2 = revision_2
        self.lines = self.get_lines(
            self.get_line_diff(revision_1, revision_2)
        )

    def get_line_diff(self, revision_1, revision_2):
        differ = difflib.Differ()
        return list(differ.compare(revision_1, revision_2))

    def get_rendered_lines(self):
        lines = {
            'revision_1': [],
            'revision_2': []
        }
        for line in self.lines['revision_1']:
            lines['revision_1'].append(Markup(line.render()))
        for line in self.lines['revision_2']:
            lines['revision_2'].append(Markup(line.render()))
        return lines

    def get_lines(self, line_diff):
        columns = {
            'revision_1': [],
            'revision_2': []
        }

        column_indexes = {
            'revision_1': 1,
            'revision_2': 1
        }

        last_changed_line, line_number = None, 0
        for line in line_diff:
            type = self.get_line_type(line)
            if type == 'detail' and last_changed_line is not None:
                pass
                # last_changed_line.add_detail(line)
            else:
                if type == 'removal':
                    last_changed_line = DiffLine(
                        line, column_indexes['revision_1'], type
                    )
                    columns['revision_1'].append(last_changed_line)
                    column_indexes['revision_1'] += 1

                if type == 'addition':
                    last_changed_line = DiffLine(
                        line, column_indexes['revision_2'], type
                    )
                    columns['revision_2'].append(last_changed_line)
                    column_indexes['revision_2'] += 1

                if type == 'unchanged':
                    columns['revision_1'].append(
                        DiffLine(line, column_indexes['revision_1'], type)
                    )
                    columns['revision_2'].append(
                        DiffLine(line, column_indexes['revision_2'], type)
                    )
                    column_indexes['revision_1'] += 1
                    column_indexes['revision_2'] += 1

        return columns

    def get_line_type(self, string):
        if string.startswith('+ '):
            return 'addition'
        if string.startswith('- '):
            return 'removal'
        if string.startswith('? '):
            return 'detail'
        if string.startswith('  '):
            return 'unchanged'


class ListDiffTool(BaseDiffTool):
    """Creates a line-by-line diff from two lists"""

    pass


class StringDiffTool(BaseDiffTool):
    """Creates a line-by-line diff from two strings"""

    def __init__(self, revision_1, revision_2):
        self.revision_1 = revision_1.splitlines()
        self.revision_2 = revision_2.splitlines()
        self.lines = self.get_lines(
            self.get_line_diff(self.revision_1, self.revision_2)
        )


class DiffLine(object):

    def __init__(self, line, line_number, type):
        self.line = line
        self.type = type
        self.line_number = line_number

    def render(self):
        return u"<td class='line-number'>{}</td><td class='{}'>{}</td>".format(
            self.line_number, self.type, self.line[2:]
        )

    def add_detail(self, line):
        self.detail_line = line
