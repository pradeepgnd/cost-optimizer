#!/bin/sh
set -eu

# These are LocalStack-only dummy S3 credentials, not AWS account credentials
# and not the LocalStack account activation token.
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION=us-east-1

bucket=cost-optimizer-data
if ! awslocal s3api head-bucket --bucket "$bucket" >/dev/null 2>&1; then
    awslocal s3api create-bucket --bucket "$bucket" >/dev/null
fi
awslocal s3 sync /opt/cost-optimizer-fixtures/ "s3://$bucket/cost-optimizer/v1/" --only-show-errors
printf 'Cost optimizer setup fixtures uploaded to the LocalStack S3 bucket.\n'
