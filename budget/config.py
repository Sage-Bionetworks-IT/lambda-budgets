import os
from pathlib import Path

from cerberus import Validator
import yaml

class Config:

  _budget_rules_schema = {
    'teams': {
      'type': 'dict',
      'required': True,
      'valuesrules': {
        'type': 'dict',
        'require_all': True,
        'schema': {
          'amount': {
            'type': 'string'
          },
          'period': {
            'type': 'string',
            'allowed': ['DAILY', 'MONTHLY', 'QUARTERLY', 'ANNUALLY']
          },
          'unit': {
            'type': 'string',
            'allowed': ['USD']
          },
          'community_manager_emails': {
            'type': 'list',
            'minlength': 1,
            'schema': {
              'type': 'string'
            }
          }
        }
      },
    }
  }

  _thresholds_schema = {
    'notify_user_only': {
      'required': True,
      'type': 'list',
      'minlength': 1,
      'schema': {
          'type': 'float'
      }
    },
    'notify_admins_too': {
      'required': True,
      'type': 'list',
      'minlength': 1,
      'schema': {
          'type': 'float'
      }
    }
  }


  def __init__(self):

    self._account_id = Config._get_env_var('AWS_ACCOUNT_ID')
    self._synapse_team_member_list_endpoint = Config._get_env_var(
      'SYNAPSE_TEAM_MEMBER_LIST_ENDPOINT'
      )
    self._notification_topic_arn = Config._get_env_var('NOTIFICATION_TOPIC_ARN')
    self.budget_rules = Config._get_config_file(
      Config._get_env_var('BUDGET_RULES_FILE_PATH')
      )
    self.thresholds = Config._get_config_file(
      Config._get_env_var('THRESHOLDS_FILE_PATH')
      )


  def __str__(self):
    return str(self.__dict__)


  @property
  def account_id(self):
    '''AWS account id'''
    return self._account_id


  @property
  def synapse_team_member_list_endpoint(self):
    '''The endpoint used to look up members of a synapse team'''
    return self._synapse_team_member_list_endpoint


  @property
  def notification_topic_arn(self):
    '''The ARN of an AWS SNS topic

    The topic which will be registered with the AWS budgets API
    for the purpose of sending notifications to users
    '''
    return self._notification_topic_arn


  @property
  def budget_rules(self):
    '''A dictionary containing the rules that are used for budget creation.

    While the rules are divided up by team, they are applied per user.
    For example, if team "A" has a budget amount "10", then each member
    of team "A" will have a budget for 10 dollars made. See the
    _budget_rules_schema for the structure of _budget_rules.
    '''
    return self._budget_rules


  @budget_rules.setter
  def budget_rules(self, candidate_budget_rules):
    Config._validate_config(self._budget_rules_schema, candidate_budget_rules)
    self._budget_rules = candidate_budget_rules


  @property
  def thresholds(self):
    '''A dictionary containing budget threshold levels.

    Budget threshold levels are used to send notifications, to either the
    user only or to the user and any team administrators. See the
    _thresholds_schema for the structure of _thresholds.
    '''
    return self._thresholds


  @thresholds.setter
  def thresholds(self, candidate_thresholds):
    Config._validate_config(self._thresholds_schema, candidate_thresholds)
    self._thresholds = candidate_thresholds


  def get_synapse_team_member_url(self, team_id):
    return f'{self.synapse_team_member_list_endpoint}/{team_id}'


  def _get_env_var(name):
    value = os.getenv(name)
    if not value:
      raise ValueError(('Lambda configuration error: '
        f'missing environment variable {name}'))
    return value


  def _get_config_file(filepath):
    try:
      with open(filepath) as config_file:
        output = yaml.full_load(config_file)
    except yaml.YAMLError as e:
      error_message = (
        'There was an error while parsing the config file at '
        f'{filepath}. Error details: {e}'
        )
      raise Exception(error_message)

    return output


  def _validate_config(schema, config):
    validator = Validator(schema)
    valid = validator.validate(config)
    if not valid:
      raise Exception(f'There was a configuration validation error: '
        f'{validator.errors}. Configuration submitted: {config}')
