# lambda-budgets
Lambda that runs on a cron to create AWS Budgets.

## Development

### Contributions
Contributions are welcome.

### Setup Development Environment

Install the following applications:
* [AWS CLI](https://github.com/aws/aws-cli)
* [AWS SAM CLI](https://github.com/aws/aws-sam-cli)
* [pre-commit](https://github.com/pre-commit/pre-commit)
* [pipenv](https://github.com/pypa/pipenv)

### Install Requirements

Run `pipenv install --dev` to install both production and development
requirements, and `pipenv shell` to activate the virtual environment. For more
information see the [pipenv docs](https://pipenv.pypa.io/en/latest/).

After activating the virtual environment, run `pre-commit install` to install
the [pre-commit](https://pre-commit.com/) git hook.

### Update Requirements

First, make any needed updates to the base requirements in `Pipfile`, then use
`pipenv` to regenerate both `Pipfile.lock` and `requirements.txt`.

```shell script
$ pipenv update --dev
```

We use `pipenv` to control versions in testing, but `sam` relies on
`requirements.txt` directly for building the lambda artifact, so we dynamically
generate `requirements.txt` from `Pipfile.lock` before building the artifact.
The file must be created in the `CodeUri` directory specified in
`template.yaml`.

```shell script
$ pipenv requirements > requirements.txt
```

Additionally, `pre-commit` manages its own requirements.

```shell script
$ pre-commit autoupdate
```

#### Environment Variables
The lambda requires certain environment varibles:
* `NOTIFICATION_TOPIC_ARN`: an SNS topic that the AWS budgets API will use to send notifications to users.
* `AWS_ACCOUNT_ID`: the account where the lambda runs. This is used to construct role ARNs and work with budgets. The assumption is that there will be no cross-account budget creation.
* `END_USER_ROLE_NAME`: the name of the AWS IAM role used to access the service catalog by users who require that a budget be made. The assumption is that there will only be one such named role.
* `BUDGET_RULES`: a yaml-format string that contains the rules used for budget creation. To get an idea of what this should look like, see `_budget_rules_schema` in `config.py`.
* `THRESHOLDS`: a yaml-format string that defines threshold levels used to send notifications. To get an idea of what this should look like, see `_thresholds_schema` in `config.py`.

The example file `sam-local-envvars.json` at the root of this project, which is
used to run the lambda function locally, contains examples of the environment
variables. For a real deployment the variables are defined in `template.yaml`;
some are derived or have defaults, but others require configuration.

Note: When the Lambda runs, `config.py` validates that the required parameters are present and, if not, stops the Lambda.

### Create a local build

Use a Lambda-like docker container to build the Lambda artifact

```shell script
$ sam build --use-container
```

### Run unit tests

Tests are defined in the `tests` folder in this project, and dependencies are
managed with `pipenv`. Install the development dependencies and run the tests
using `coverage`.

```shell script
$ pipenv run coverage run -m pytest tests/ -svv
```

Automated testing will upload coverage results to [Coveralls](coveralls.io).

### Run locally

Run the command below, where `my-profile` is an AWS profile with the correct
permissions, and you've edited the `sam-local-envvars.json` file to have
meaningful values for the required environment variables.

```shell script
$ sam local invoke BudgetMakerFunction --event events/event.json --profile my-profile -n sam-local-envvars.json
```

## Deployment

### Build

```shell script
sam build
```

## Deploy Lambda to S3
This requires the correct permissions to upload to bucket
`bootstrap-awss3cloudformationbucket-19qromfd235z9` and
`essentials-awss3lambdaartifactsbucket-x29ftznj6pqw`

```shell script
sam package --template-file .aws-sam/build/template.yaml \
  --s3-bucket essentials-awss3lambdaartifactsbucket-x29ftznj6pqw \
  --output-template-file .aws-sam/build/lambda-budgets.yaml

aws s3 cp .aws-sam/build/lambda-budgets.yaml s3://bootstrap-awss3cloudformationbucket-19qromfd235z9/lambda-budgets/master/
```

## Install Lambda into AWS
Create the following [sceptre](https://github.com/Sceptre/sceptre) file

config/prod/lambda-template.yaml
```yaml
template_path: "remote/lambda-budgets.yaml"
stack_name: "lambda-budgets"
stack_tags:
  Department: "Platform"
  Project: "Infrastructure"
  OwnerEmail: "it@sagebase.org"
hooks:
  before_launch:
    - !cmd "curl https://s3.amazonaws.com/bootstrap-awss3cloudformationbucket-19qromfd235z9/lambda-template/master/lambda-budgets.yaml --create-dirs -o templates/remote/lambda-budgets.yaml"
```

Install the lambda using sceptre:
```shell script
sceptre --var "profile=my-profile" --var "region=us-east-1" launch prod/lambda-budgets.yaml
```

## Author

Your Name Here.
