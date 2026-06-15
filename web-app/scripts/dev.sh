
set -e

FILE=~/.config/gcloud/application_default_credentials.json

# gcloud auth login && gcloud auth application-default login

export GOOGLE_APPLICATION_CREDENTIALS=$FILE

export TOKEN=$(gcloud auth print-access-token) 

next dev --turbopack