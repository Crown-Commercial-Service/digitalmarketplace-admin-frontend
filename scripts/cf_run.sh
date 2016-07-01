#!/bin/sh

set -ex

. venv/bin/activate
python application.py runprodserver
