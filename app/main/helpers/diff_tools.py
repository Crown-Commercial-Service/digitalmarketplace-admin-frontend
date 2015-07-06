import difflib
from abc import ABCMeta, abstractmethod
from flask import Markup, escape


class BaseDiffTool(object):
    """
    Creates a line-by-line diff from two lists of items
    """
    __metaclass__ = ABCMeta

    @abstractmethod
    def __init__(self, revision_1, revision_2, if_unchanged):
        # revisions are lists of strings to diff against each other
        self.revision_1 = revision_1
        self.revision_2 = revision_2
        self.include_unchanged_lines_in_output = if_unchanged
        self.lines = self._get_lines()

    def render_lines(self):
        """
        Returns rendered HTML lines to be displayed in a diff page
        """

        lines = {
            'revision_1': [],
            'revision_2': []
        }
        for index, line in enumerate(self.lines['revision_1']):
            lines['revision_1'].append(
                Markup(self._render_words_html(
                    self.lines['revision_1'][index], index+1)
                )
            )
            lines['revision_2'].append(
                Markup(self._render_words_html(
                    self.lines['revision_2'][index], index+1)
                )
            )

        return lines

    def _get_lines(self):
        """
        Turns a pair of input lines into a list of word diffs

        In:
        self.revision_1: ['Hi there', 'Less letters']
        self.revision_2: ['Hi there!', 'Less let']

        Out:
        self.lines: { 'revision_1': ['  Hi', '- there'], ['  Less', '- letters'],
                      'revision_2': ['  Hi', '+ there!'], ['  Less', '+ let'] }
        """

        lines = {
            'revision_1': [],
            'revision_2': []
        }

        # Make sure lists of strings are same length
        # Pad the shorter list with empty strings if necessary
        # Also means pair of lists in returned dictionary are of equal length
        revision_1, revision_2 = self._pad_lists_to_max_length(
            self.revision_1, self.revision_2)

        for index, string in enumerate(revision_1):

            diff = self._get_words_diff(revision_1[index], revision_2[index])

            # create an array of removed words and one of added rows
            revision_1_words, revision_2_words = \
                self._split_words_diff(diff)

            # if revisions are equal and we want to skip unchanged lines
            if revision_1_words == revision_2_words \
                and self._get_line_type(revision_1_words) == 'unchanged' \
                and self._get_line_type(revision_2_words) == 'unchanged' \
                    and not self.include_unchanged_lines_in_output:
                continue

            lines['revision_1'].append(revision_1_words)
            lines['revision_2'].append(revision_2_words)

        return lines

    def _split_words_diff(self, words_diff):
        """
        Accepts a list of words that have been diffed
        Returns two lists: one with removals ('-') and one with additions ('+')
        Ignores detail ('?') lines

        In:  ['  Hi', '- there', '+ there!', '?      +\n']
        Out: (['  Hi', '- there'], ['  Hi', '+ there!'])
        """

        words = {
            'removal': [],
            'addition': []
        }

        for word in words_diff:
            type = self._get_word_type(word)
            if type == 'detail':
                pass

            else:
                if type == 'removal':
                    words[type].append(word)

                if type == 'addition':
                    words[type].append(word)

                if type == 'unchanged':
                    for key in words.keys():
                        words[key].append(word)

        return words['removal'], words['addition']

    def _render_words_html(self, words, line_number):

        def _render_words_inner_html(words, inferred_type):

            html_words = []

            for word in words:
                word = escape(word)
                type = self._get_word_type(word)

                if type == 'unchanged':
                    html_words.append(u"{}".format(word[2:]))

                elif type == inferred_type:
                    html_words.append(u"<strong>{}</strong>".format(word[2:]))

            return ' '.join(html_words).replace(u'</strong> <strong>', ' ')

        # Can only have one inferred type per line
        inferred_type = self._get_line_type(words)

        return \
            u"<td class='line-number line-number-{type}'>{line_number}</td>" \
            u"<td class='line-content {type}'>{line}</td>".format(
                type=inferred_type,
                line_number=line_number,
                line=_render_words_inner_html(words, inferred_type)
            )

    @staticmethod
    def _get_words_diff(revision_1_line, revision_2_line):
        """
        Accepts two strings which are split into lists
        Returns a list of word-diffs

        In:  'Hi there', 'Hi there!'
        Out: ['  Hi', '- there', '+ there!', '?      +\n']
        """
        differ = difflib.Differ()
        # Splitting the lines on whitespace to that we get a word diff
        return list(differ.compare(
            revision_1_line.split(), revision_2_line.split()
        ))

    @staticmethod
    def _pad_lists_to_max_length(list_1, list_2, padding=''):
        """
        if lists are not the same length,
        pad the shorter list to the length of the longest list
        with a given placeholder element

        In:  [ 1, 2, 3, 4 ], [ 1, 2 ], 'new'
        Out: [ 1, 2, 3, 4 ], [ 1, 2, 'new', 'new']
        """

        def _pad_list_to_max_length(list, new_length, padding):
            return list + [padding] * (new_length - len(list))

        # if same length, return
        if len(list_1) == len(list_2):
            return list_1, list_2

        max_len = max(len(list_1), len(list_2))

        return \
            _pad_list_to_max_length(list_1, max_len, padding), \
            _pad_list_to_max_length(list_2, max_len, padding)

    @staticmethod
    def _get_line_type(words, types_to_look_for=None):

        if not words:
            return 'empty'

        if not types_to_look_for:
            types_to_look_for = ['addition', 'removal']

        for word in words:
            type = BaseDiffTool._get_word_type(word)
            if type in types_to_look_for:
                return type

        # if words is empty, this is still what we want
        return 'unchanged'

    @staticmethod
    def _get_word_type(string):
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

    def __init__(self, revision_1, revision_2, if_unchanged=False):

        if not self._is_list(revision_1) or not self._is_list(revision_2):
            err = ""

            if not self._is_list(revision_1):
                err += " First parameter is of type {}.".format(
                    type(revision_1)
                )

            if not self._is_list(revision_2):
                err += " Second parameter is of type {}.".format(
                    type(revision_2)
                )

            raise ValueError(
                "ListDiffTool requires two list parameters. {}".format(err)
            )

        super(
            ListDiffTool, self).__init__(revision_1, revision_2, if_unchanged)

    @staticmethod
    def _is_list(value):
        return type(value).__name__ == 'list'


class StringDiffTool(BaseDiffTool):
    """Creates a line-by-line diff from two strings"""

    def __init__(self, revision_1, revision_2, if_unchanged=False):

        if not self._is_string(revision_1) or not self._is_string(revision_2):
            err = ""

            if not self._is_string(revision_1):
                err += " First parameter is of type {}.".format(
                    type(revision_1)
                )

            if not self._is_string(revision_2):
                err += " Second parameter is of type {}.".format(
                    type(revision_2)
                )

            raise ValueError(
                "StringDiffTool requires two string parameters. {}".format(err)
            )

        super(StringDiffTool, self).__init__(
            revision_1.splitlines(), revision_2.splitlines(), if_unchanged
        )

    @staticmethod
    def _is_string(value):
        return type(value).__name__ == 'str' \
            or type(value).__name__ == 'unicode'
