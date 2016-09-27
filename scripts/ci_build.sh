#!/bin/sh
npm install
pip install -U -r requirements_for_test.txt
npm run frontend-build:production
