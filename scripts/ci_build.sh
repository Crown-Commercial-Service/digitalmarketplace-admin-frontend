#!/bin/sh
npm install
pip install -r requirements.txt
pip install -r requirements_for_test.txt
npm run frontend-build:production
