from .. import main


def get_template_data(**kwargs):
    template_data = dict(main.config['BASE_TEMPLATE_DATA'], **kwargs)
    return template_data
