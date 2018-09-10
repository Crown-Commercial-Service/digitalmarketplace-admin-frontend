# Digital Marketplace admin frontend

[![Coverage Status](https://coveralls.io/repos/alphagov/digitalmarketplace-admin-frontend/badge.svg?branch=master&service=github)](https://coveralls.io/github/alphagov/digitalmarketplace-admin-frontend?branch=master)
[![Requirements Status](https://requires.io/github/alphagov/digitalmarketplace-admin-frontend/requirements.svg?branch=master)](https://requires.io/github/alphagov/digitalmarketplace-admin-frontend/requirements/?branch=master)


Frontend administration application for the digital marketplace.

- Python app, based on the [Flask framework](http://flask.pocoo.org/)

## Quickstart

Install dependencies, build assets and run the app
```
make run-all
```

## Full setup

Create a virtual environment
```
python3 -m venv ./venv
```

### Activate the virtual environment
```
source ./venv/bin/activate
```

### Upgrade dependencies

Install new Python dependencies with pip

```make requirements-dev```

Install frontend dependencies with yarn and gulp
[How to install yarn](https://yarnpkg.com/en/docs/install)

```
yarn
```

### Compile the front-end code

You need Node (try to install the version we use in production -
 see the [base docker image](https://github.com/alphagov/digitalmarketplace-docker-base/blob/master/base.docker)).

To check the version you're running, type:

```
node --version
```


### Run the tests

```
make test
```


### Run the development server

To run the Admin Frontend App for local development use the `run-all` target.
This will install requirements, build assets and run the app.

```
make run-all
```

To just run the application use the `run-app` target.

The admin frontend runs on port 5004. Use the app at [http://127.0.0.1:5004/admin/](http://127.0.0.1:5004/admin/)

### Updating application dependencies

`requirements.txt` file is generated from the `requirements-app.txt` in order to pin
versions of all nested dependencies. If `requirements-app.txt` has been changed (or
we want to update the unpinned nested dependencies) `requirements.txt` should be
regenerated with

```
make freeze-requirements
```

`requirements.txt` should be commited alongside `requirements-app.txt` changes.

## Frontend tasks

[YARN](https://yarnpkg.com/en/) is used for all frontend build tasks. The commands available are:

- `yarn run frontend-build:development` (compile the frontend files for development)
- `yarn run frontend-build:production` (compile the frontend files for production)
- `yarn run frontend-build:watch` (watch all frontend files & rebuild when anything changes)
