import yaml

content_folder = "bower_components/digital-marketplace-ssp-content/g6/"

def get_pages():
    page_order_yaml = open("app/page_order.yml", "r")
    page_order = yaml.load(page_order_yaml)
    pages_with_questions = map(__populate_page__, page_order)
    return page_order

def __populate_page__(page):
    page['questions'] = map(__get_question_content__, page['questions'])
    return page

def __get_question_content__(question):
    question_yaml = open(content_folder + question + ".yml", "r")
    question_content = yaml.load(question_yaml)
    question_content['id'] = question
    return question_content
