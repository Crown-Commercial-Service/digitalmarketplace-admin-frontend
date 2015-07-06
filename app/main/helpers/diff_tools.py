import difflib
from datetime import datetime
from flask import Markup, escape
from flask._compat import string_types
from dmutils.formats import DATETIME_FORMAT
from ... import DISPLAY_DATETIME_FORMAT


def get_diffs_from_service_data(
        sections_to_diff=None,
        sections=None,
        revision_1=None,
        revision_2=None,
        include_unchanged_lines_in_output=False
):
    def all_are_lists(*args):
        return all(isinstance(arg, list) for arg in args)

    def all_are_strings(*args):
        return all(isinstance(arg, string_types) for arg in args)

    diffs = []

    for section in sections:
        if section['name'] in sections_to_diff:
            for question in section['questions']:
                revisions_are_valid = True
                question_revision_1 = revision_1[question['id']]
                question_revision_2 = revision_2[question['id']]

                if all_are_lists(question_revision_1, question_revision_2):
                    pass

                elif all_are_strings(question_revision_1, question_revision_2):
                    question_revision_1 = question_revision_1.splitlines()
                    question_revision_2 = question_revision_2.splitlines()

                else:
                    revisions_are_valid = False

                if revisions_are_valid:
                    question_diff = render_lines(
                        question_revision_1,
                        question_revision_2,
                        include_unchanged_lines_in_output
                    )

                    # if arrays are empty, there are no changes for this question
                    if question_diff['revision_1'] or question_diff['revision_2']:
                        diffs.append({
                            'section_name': section['name'],
                            'label': question['question'],
                            'revisions':
                                [val + question_diff['revision_2'][i]
                                 for i, val
                                 in enumerate(question_diff['revision_1'])]
                        })

    return diffs


def get_revision_dates(revision_1=None, revision_2=None):

    def get_revision_date(date_string):
        # Tuesday, 10 June 2015 at 14:00
        return datetime.strptime(
            date_string, DATETIME_FORMAT
        ).strftime(DISPLAY_DATETIME_FORMAT)

    return {
        'revision_1': get_revision_date(revision_1['updatedAt']),
        'revision_2': get_revision_date(revision_2['updatedAt'])
    }


def render_lines(
        revision_1, revision_2, include_unchanged_lines_in_output=False):
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
    revision_1, revision_2 = pad_lists_to_max_length(revision_1, revision_2)

    for index, string in enumerate(revision_1):

        diff = get_words_diff(revision_1[index], revision_2[index])

        # create an array of removed words and one of added rows
        revision_1_words, revision_2_words = split_words_diff(diff)

        # if revisions are equal and we want to skip unchanged lines
        if revision_1_words == revision_2_words \
            and get_line_type(revision_1_words) == 'unchanged' \
            and get_line_type(revision_2_words) == 'unchanged' \
                and not include_unchanged_lines_in_output:
            continue

        lines['revision_1'].append(
            Markup(render_words_html(revision_1_words, index+1))
        )
        lines['revision_2'].append(
            Markup(render_words_html(revision_2_words, index+1))
        )

    return lines


def split_words_diff(words_diff):
    """
    Accepts a list of words that have been diffed
    Returns two lists: one with removals ('-') and one with additions ('+')
    Ignores detail ('?') lines

    In:  ['  Hi', '- there', '+ there!', '?      +\n']
    Out: (['  Hi', '- there'], ['  Hi', '+ there!'])
    """

    return [w for w in words_diff
            if get_word_type(w) in ['unchanged', 'removal']], \
           [w for w in words_diff
            if get_word_type(w) in ['unchanged', 'addition']]


def render_words_html(words, line_number):

    def _render_words_inner_html(words, inferred_type):

        html_words = []

        for word in words:
            word = escape(word)
            type = get_word_type(word)

            if type == 'unchanged':
                html_words.append(u"{}".format(word[2:]))

            elif type == inferred_type:
                html_words.append(u"<strong>{}</strong>".format(word[2:]))

        return ' '.join(html_words).replace(u'</strong> <strong>', ' ')

    # Can only have one inferred type per line
    inferred_type = get_line_type(words)

    return \
        u"<td class='line-number line-number-{type}'>{line_number}</td>" \
        u"<td class='line-content {type}'>{line}</td>".format(
            type=inferred_type,
            line_number=line_number,
            line=_render_words_inner_html(words, inferred_type)
        )


def get_words_diff(revision_1_line, revision_2_line):
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


def pad_lists_to_max_length(list_1, list_2, padding=''):
    """
    if lists are not the same length,
    pad the shorter list to the length of the longest list
    with a given placeholder element

    In:  [ 1, 2, 3, 4 ], [ 1, 2 ], 'new'
    Out: [ 1, 2, 3, 4 ], [ 1, 2, 'new', 'new']
    """

    def pad_list_to_max_length(list, new_length, padding):
        return list + [padding] * (new_length - len(list))

    # if same length, return
    if len(list_1) == len(list_2):
        return list_1, list_2

    max_len = max(len(list_1), len(list_2))

    return pad_list_to_max_length(list_1, max_len, padding), \
        pad_list_to_max_length(list_2, max_len, padding)


def get_line_type(words, types_to_look_for=None):

    if not words:
        return 'empty'

    if not types_to_look_for:
        types_to_look_for = ['addition', 'removal']

    for word in words:
        type = get_word_type(word)
        if type in types_to_look_for:
            return type

    # if words is empty, this is still what we want
    return 'unchanged'


def get_word_type(string):
    if string.startswith('+ '):
        return 'addition'
    if string.startswith('- '):
        return 'removal'
    if string.startswith('? '):
        return 'detail'
    if string.startswith('  '):
        return 'unchanged'
