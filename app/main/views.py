from . import main


@main.route('/')
def index():
    return "Hello, Nicole!", 200
