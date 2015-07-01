import difflib
from flask import Markup


class BaseDiffTool(object):
    """Creates a line-by-line diff from two lists of items"""

    def __init__(self, revision_1, revision_2, if_unchanged=False):
        self.revision_1 = revision_1  # list of multiple-word strings
        self.revision_2 = revision_2  # list of multiple-word strings
        self.include_unchanged_lines_in_output = if_unchanged

        # pass in both revisions
        self.lines = self._render_lines(self.revision_1, self.revision_2)

    def _get_words_diff(self, revision_1, revision_2):
        differ = difflib.Differ()
        # Splitting the lines on whitespace to that we get a word diff
        return list(differ.compare(revision_1.split(), revision_2.split()))

    def _split_words_diff(self, words_diff):

        revision_1_words = []
        revision_2_words = []
        is_unchanged = True

        for word in words_diff:
            type = self._get_line_type(word)
            if type == 'detail':
                pass
                # i don't need you
            else:
                if type == 'removal':
                    is_unchanged = False
                    revision_1_words.append(word)

                if type == 'addition':
                    is_unchanged = False
                    revision_2_words.append(word)

                if type == 'unchanged':
                    revision_1_words.append(word)
                    revision_2_words.append(word)

        return revision_1_words, revision_2_words, is_unchanged

    def _render_words_inner_html(self, words, expected_type):

        html_words = []

        for word in words:
            type = self._get_line_type(word)
            if type == 'unchanged':
                html_words.append(word[2:])

            if type == expected_type:
                html_words.append("<strong>{}</strong>".format(word[2:]))

        return ' '.join(html_words).replace('</strong> <strong>', ' ')

    def _render_words_html(self, words, expected_type, line_number):

        return \
            u"<tr class='diff--row'>" \
            u"<td class='number line-number {type}'>{line_number}</td>" \
            u"<td class='{type}'>{line}</td>" \
            u"</tr>".format(
                type=expected_type,
                line_number=line_number,
                line=self._render_words_inner_html(words, expected_type)
            )

    def _render_lines(self, revision_1, revision_2):
        lines = {
            'revision_1': [],
            'revision_2': []
        }

        # TODO: don't assume lists of same length
        for index, string in enumerate(revision_1):
            line = self._get_words_diff(revision_1[index], revision_2[index])

            revision_1_words, revision_2_words, is_unchanged = \
                self._split_words_diff(line)

            # if this line is unchanged and we don't want unchanged lines
            if is_unchanged and not self.include_unchanged_lines_in_output:
                continue

            lines['revision_1'].append(Markup(
                self._render_words_html(revision_1_words, 'removal', index+1)
            ))

            lines['revision_2'].append(Markup(
                self._render_words_html(revision_2_words, 'addition', index+1)
            ))

        return lines

    def get_lines(self):
        return self.lines

    @staticmethod
    def _get_line_type(string):
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

    def __init__(self, revision_1, revision_2, if_unchanged=False):
        self.revision_1 = revision_1.splitlines()
        self.revision_2 = revision_2.splitlines()
        self.include_unchanged_lines_in_output = if_unchanged
        self.lines = self._render_lines(self.revision_1, self.revision_2)
