set -ex

sam build
sam package --profile admincentral-cfn --template-file .aws-sam/build/template.yaml \
  --s3-bucket essentials-awss3lambdaartifactsbucket-x29ftznj6pqw \
  --output-template-file .aws-sam/build/lambda-budgets.yaml
aws --profile admincentral-cfn s3 cp .aws-sam/build/lambda-budgets.yaml \
  s3://bootstrap-awss3cloudformationbucket-19qromfd235z9/lambda-budgets/master/

set +ex
