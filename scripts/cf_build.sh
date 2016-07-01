#!/bin/sh

set -eux

diy-install-python
. venv/bin/activate
# FIXME: PyYAML tries to compile libyaml bindings if it finds a working compiler, and fails because Python headers are missing.
# Temporary workaround is to stop the compiler from working.
export CFLAGS="-fborkborkbork"
pip install -r requirements.txt

diy-install-node
# "no" to request to report usage statistics.  Not suitable for a cloud deployment.
yes no | npm install
npm run frontend-build:production 1>&2
