from .. import main
from ..helpers.auth import is_authenticated


def get_template_data(merged_with=None):
    if merged_with is None:
        merged_with = dict()
    template_data = dict(main.config['BASE_TEMPLATE_DATA'], **merged_with)
    template_data["authenticated"] = is_authenticated()
    return template_data
