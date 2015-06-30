from .. import main


def get_template_data(merged_with=None):
    if merged_with is None:
        merged_with = dict()
    template_data = dict(main.config['BASE_TEMPLATE_DATA'], **merged_with)
    return template_data
