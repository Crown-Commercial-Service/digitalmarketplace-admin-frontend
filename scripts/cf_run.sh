#!/bin/sh

set -ex

python ./.local/python/virtualenv_tools.py --update-path="$PWD/venv" venv

. venv/bin/activate
python application.py runserver
