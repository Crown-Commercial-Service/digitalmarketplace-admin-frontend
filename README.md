# digitalmarketplace-admin-frontend

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
export DM_API_URL=http://localhost:5000
export DM_ADMIN_FRONTEND_API_AUTH_TOKEN=<bearer_token>
export DM_ADMIN_FRONTEND_PASSWORD_HASH=<generated password hash>
```
You can generate a password hash by running `python ./scripts/generate_password.py`.


### Upgrade dependencies

Install new Python dependencies with pip

```pip install -r requirements_for_test.txt```

Install frontend dependencies with npm and gulp

```
npm install
```

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

The admin frontend runs on port 5004. Use the app at [http://127.0.0.1:5004/](http://127.0.0.1:5004/)

## Frontend tasks

[NPM](https://www.npmjs.org/) is used for all frontend build tasks. The commands available are:

- `npm run frontend-build:development` (compile the frontend files for development)
- `npm run frontend-build:production` (compile the frontend files for production)
- `npm run frontend-build:watch` (watch all frontend files & rebuild when anything changes)
- `npm run frontend-install` (install all non-NPM dependancies)

Note: `npm run frontend-install` is run as a post-install task after you run `npm install`.
