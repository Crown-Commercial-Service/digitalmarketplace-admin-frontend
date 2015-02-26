import yaml, inflection, re

content_folder = "bower_components/digital-marketplace-ssp-content/g6/"

def get_sections():
    section_order = yaml.load(
        open("app/section_order.yml", "r")
    )
    map(__populate_section__, section_order)
    return section_order

def get_section(requested_section):
    sections = get_sections()
    for section in sections:
        if section['id'] == requested_section: return section

def __populate_section__(section):
    section['questions'] = map(__get_question_content__, section['questions'])
    section['id'] = __make_id__(section['name'])
    return section

def __get_question_content__(question):
    question_content = yaml.load(
        open(content_folder + question + ".yml", "r")
    )
    question_content['id'] = question
    if 'dependsOnLots' in question_content:
        question_content['dependsOnLots'] = [x.strip() for x in question_content['dependsOnLots'].lower().split(',')]
    else:
        question_content['dependsOnLots'] = ["saas", "paas", "iaas", "scs"]
    return question_content

def __match_section_id__(section):
    return True

def __make_id__(name):
    return inflection.underscore(
        re.sub("\s", "_", name)
    )
