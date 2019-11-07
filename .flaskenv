DM_API_PORT=5000
DM_ADMIN_PORT=5004

FLASK_APP=application:application
FLASK_ENV=development
FLASK_RUN_EXTRA_FILES=app/content/frameworks/
FLASK_RUN_PORT=${DM_ADMIN_PORT}
