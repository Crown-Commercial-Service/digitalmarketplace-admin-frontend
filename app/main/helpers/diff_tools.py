import difflib
from flask import Markup


class BaseDiffTool(object):
    """Creates a line-by-line diff from two lists of items"""

    def __init__(self, revision_1, revision_2):
        self.revision_1 = revision_1
        self.revision_2 = revision_2
        self.line_diff = self.get_line_diff(revision_1, revision_2)
        self.lines = self.get_lines()

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

    def get_lines(self):
        columns = {
            'revision_1': [],
            'revision_2': []
        }
        revision_1_number, revision_2_number = 1, 1
        last_changed_line = None
        for line in self.line_diff:
            type = self.get_line_type(line)
            if type == 'detail' and last_changed_line is not None:
                last_changed_line.add_detail(line)
            else:
                if type == 'removal':
                    diff_line = DiffLine(line, 'revision_1', type)
                    columns['revision_1'].append(diff_line)
                    last_changed_line = diff_line
                if type == 'addition':
                    diff_line = DiffLine(line, 'revision_2', type)
                    columns['revision_2'].append(diff_line)
                    last_changed_line = diff_line
                if type == 'unchanged':
                    columns['revision_1'].append(
                        DiffLine(line, 'revision_1', 'unchanged')
                    )
                    columns['revision_2'].append(
                        DiffLine(line, 'revision_2', 'unchanged')
                    )
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
        self.line_diff = self.get_line_diff(self.revision_1, self.revision_2)
        self.lines = self.get_lines()


class DiffLine(object):
    column_indexes = {
        'revision_1': 1,
        'revision_2': 1
    }

    def __init__(self, line, column, change):
        self.line = line
        self.type = change
        self.line_number = DiffLine.column_indexes[column]
        DiffLine.column_indexes[column] += 1

    def render(self):
        return u"<td>{}</td><td><span class='{}'>{}</span></td>".format(
            self.line_number, self.type, self.line[2:]
        )

    def add_detail(self, line):
        self.detail_line = line
