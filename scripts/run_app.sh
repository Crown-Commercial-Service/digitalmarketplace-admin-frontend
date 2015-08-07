#!/bin/bash
if [ -n "$VIRTUAL_ENV" ]; then
  echo "Already in virtual environment $VIRTUAL_ENV"
else
  source ./venv/bin/activate 2>/dev/null && echo "Virtual environment activated."
fi

# Use default environment vars for localhost if not already set
export DM_DATA_API_URL=${DM_DATA_API_URL:=http://localhost:5000}
export DM_DATA_API_AUTH_TOKEN=${DM_DATA_API_AUTH_TOKEN:=myToken}
# Default hash for user/pass combo: admin/admin
export DM_ADMIN_FRONTEND_COOKIE_SECRET=${DM_ADMIN_FRONTEND_COOKIE_SECRET:=secret}
export DM_S3_DOCUMENT_BUCKET=${DM_S3_DOCUMENT_BUCKET:=admin-frontend-dev-documents}
export DM_MANDRILL_API_KEY=${DM_MANDRILL_API_KEY:=not_a_real_key}
export DM_SHARED_EMAIL_KEY=${DM_SHARED_EMAIL_KEY:=verySecretKey}

echo "Environment variables in use:"
env | grep DM_

python application.py runserver
