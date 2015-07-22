import difflib
try:
    from itertools import izip_longest
except ImportError:
    from itertools import zip_longest as izip_longest
from datetime import datetime
from flask import Markup, escape
from flask._compat import string_types
from dmutils.formats import DATETIME_FORMAT
from ... import DISPLAY_DATETIME_FORMAT


def get_diffs_from_service_data(
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
        for question in section['questions']:
            revisions_are_valid = True
            question_revision_1 = revision_1.get(question['id'], [])
            question_revision_2 = revision_2.get(question['id'], [])

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
    revision_1: ['Hi there', 'Less letters']
    revision_2: ['Hi there!', 'Less let']

    Out:
    { 'revision_1': ['  Hi', '- there'], ['  Less', '- letters'],
      'revision_2': ['  Hi', '+ there!'], ['  Less', '+ let'] }
    """

    lines = {
        'revision_1': [],
        'revision_2': []
    }

    for index, revisions in enumerate(
            izip_longest(revision_1, revision_2, fillvalue='')
    ):
        diff = get_words_diff(revisions[0], revisions[1])

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
