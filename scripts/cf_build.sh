#!/bin/sh

set -eux

diy-install-python
. venv/bin/activate
pip install -r requirements.txt

diy-install-node
# "no" to request to report usage statistics.  Not suitable for a cloud deployment.
yes no | npm install
npm run frontend-build:production 1>&2
