#!/bin/sh

set -eux

NODE=https://nodejs.org/dist/v4.4.7/node-v4.4.7-linux-x64.tar.xz

VIRTUALENV='https://pypi.python.org/packages/5c/79/5dae7494b9f5ed061cff9a8ab8d6e1f02db352f3facf907d9eb614fb80e9/virtualenv-15.0.2.tar.gz#md5=0ed59863994daf1292827ffdbba80a63'

cd "$BUILD_DIR"

wget --quiet -O "$CACHE_DIR/virtualenv.tar.gz" "$VIRTUALENV"
mkdir -p "$CACHE_DIR/virtualenv"
tar xf "$CACHE_DIR/virtualenv.tar.gz" --directory="$CACHE_DIR/virtualenv" --strip-components=1
python "$CACHE_DIR/virtualenv/virtualenv.py" "$BUILD_DIR/venv"
. "$BUILD_DIR/venv/bin/activate"

export CFLAGS="-fborkborkbork"
pip install -r requirements.txt

mkdir -p "$BUILD_DIR/.local/python" 
pip install -t "$BUILD_DIR/.local/python/" virtualenv-tools

wget --quiet -O "$CACHE_DIR/node.tar.xz" "$NODE"
mkdir -p "$CACHE_DIR/node"
tar xf "$CACHE_DIR/node.tar.xz" --directory="$CACHE_DIR/node" --strip-components=1
export PATH="$CACHE_DIR/node/bin:$PATH"

yes no | npm install
npm run frontend-build:production 1>&2
