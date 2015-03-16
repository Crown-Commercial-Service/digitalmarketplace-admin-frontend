#!/bin/bash
source ./venv/bin/activate 2>/dev/null && echo "Virtual environment activated."

# Use default environment vars for localhost if not already set
export DM_API_URL=${DM_API_URL:=http://localhost:5000}
export DM_ADMIN_FRONTEND_API_AUTH_TOKEN=${DM_ADMIN_FRONTEND_API_AUTH_TOKEN:=myToken}
export DM_ADMIN_FRONTEND_PASSWORD_HASH=${DM_ADMIN_FRONTEND_PASSWORD_HASH:=myHash}
export DM_DOCUMENT_S3_BUCKET='admin-frontend-dev-documents'

echo "Environment variables in use:"
env | grep DM_

python application.py runserver
