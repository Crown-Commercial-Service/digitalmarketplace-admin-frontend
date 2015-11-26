# Digital Marketplace admin frontend

[![Coverage Status](https://coveralls.io/repos/alphagov/digitalmarketplace-admin-frontend/badge.svg?branch=master&service=github)](https://coveralls.io/github/alphagov/digitalmarketplace-admin-frontend?branch=master)
[![Requirements Status](https://requires.io/github/alphagov/digitalmarketplace-admin-frontend/requirements.svg?branch=master)](https://requires.io/github/alphagov/digitalmarketplace-admin-frontend/requirements/?branch=master)


Frontend administration application for the digital marketplace.

- Python app, based on the [Flask framework](http://flask.pocoo.org/)

## Setup

Install [Virtualenv](https://virtualenv.pypa.io/en/latest/)

```
sudo easy_install virtualenv
```

Create a virtual environment

 ```
 virtualenv ./venv
 ```

 Activate the virtual environment
 ```
 source ./venv/bin/activate
 ```

Set the required environment variables (for dev use local API instance if you
have it running):
```
export DM_DATA_API_URL=http://localhost:5000
export DM_DATA_API_AUTH_TOKEN=<bearer_token>
```


### Upgrade dependencies

Install new Python dependencies with pip

```pip install -r requirements_for_test.txt```

Install frontend dependencies with npm and gulp

```
npm install
```

### Compile the front-end code

You need Node (minimum version of 0.10.0, maximum version 0.12.7) which will also get you [NPM](npmjs.org), Node's package management tool.

To check the version you're running, type:

```
node --version
```

For development usage:

```
npm run frontend-build:development
```

For production:

```
npm run frontend-build:production
```

Note: running `npm run frontend-build:watch` will also build the front-end code.

### Run the tests

```
./scripts/run_tests.sh
```


### Run the server

To run the Admin Frontend App for local development you can use the convenient run
script, which sets the required environment variables to defaults if they have
not already been set:

```
./scripts/run_app.sh
```

More generally, the command to start the server is:
```
python application.py runserver
```

The admin frontend runs on port 5004. Use the app at [http://127.0.0.1:5004/admin/](http://127.0.0.1:5004/admin/)

### Using FeatureFlags

To use feature flags, check out the documentation in (the README of)
[digitalmarketplace-utils](https://github.com/alphagov/digitalmarketplace-utils#using-featureflags).

## Frontend tasks

[NPM](https://www.npmjs.org/) is used for all frontend build tasks. The commands available are:

- `npm run frontend-build:development` (compile the frontend files for development)
- `npm run frontend-build:production` (compile the frontend files for production)
- `npm run frontend-build:watch` (watch all frontend files & rebuild when anything changes)
- `npm run frontend-install` (install all non-NPM dependancies)

Note: `npm run frontend-install` is run as a post-install task after you run `npm install`.
