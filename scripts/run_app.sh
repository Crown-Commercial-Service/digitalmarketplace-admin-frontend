#!/bin/bash
source ./venv/bin/activate 2>/dev/null && echo "Virtual environment activated."

# Use default environment vars for localhost if not already set
export DM_API_URL=${DM_API_URL:=http://localhost:5000}
export DM_ADMIN_FRONTEND_API_AUTH_TOKEN=${DM_ADMIN_FRONTEND_API_AUTH_TOKEN:=myToken}
# Default hash for user/pass combo: admin/admin
export DM_ADMIN_FRONTEND_PASSWORD_HASH=${DM_ADMIN_FRONTEND_PASSWORD_HASH:=JHA1azIkMjcxMCQxYjM5Y2JhY2RkYTY0OWMwYjdhMGU1MWU4MjQ5ODZlYSQ2VkNuM1I3dXNXYW8zY3dWZmRzVHFBck10Tzh0cWRBLg==}
export DM_ADMIN_FRONTEND_COOKIE_SECRET=${DM_ADMIN_FRONTEND_COOKIE_SECRET:=secret}
export DM_S3_DOCUMENT_BUCKET='admin-frontend-dev-documents'

echo "Environment variables in use:"
env | grep DM_

python application.py runserver
