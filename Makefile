
.DEFAULT_GOAL := bootstrap

%:
	-@[ -z "$$TERM" ] || tput setaf 1  # red
	@>&2 echo warning: calling '`make`' is being deprecated in this repo, you should use '`invoke` (https://pyinvoke.org)' instead.
	-@[ -z "$$TERM" ] || tput setaf 9  # default
	@# pass goals to '`invoke`'
	invoke $(or $(MAKECMDGOALS), $@)
	@exit

help:
	invoke --list

.PHONY: bootstrap
bootstrap:
	pip install digitalmarketplace-developer-tools
	@echo done
	-@[ -z "$$TERM" ] || tput setaf 2  # green
	@>&2 echo dmdevtools has been installed globally, run developer tasks with '`invoke`'
	-@[ -z "$$TERM" ] || tput setaf 9  # default

.PHONY: build
build:
	docker build -t digitalmarketplace-aws-admin-frontend-http --build-arg DM_APP_NAME=admin-frontend -f docker-aws/Dockerfile.http .
	docker build -t digitalmarketplace-aws-admin-frontend-wsgi -f docker-aws/Dockerfile.wsgi .
