#!/bin/bash

eval $(./scripts/ups_as_envs.py)
exec python application.py runprodserver
