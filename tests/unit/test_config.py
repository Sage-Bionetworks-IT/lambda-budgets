from pathlib import Path
import json
import unittest
from unittest.mock import MagicMock, patch

from budget.config import Config
import yaml


class TestConfig(unittest.TestCase):

  def test_init(self):
    account_id = '012345678901'
    endpoint = 'http://endpoint_placeholder'
    topic_arn = 'arn:aws:sns:us-east-1:123456789012:mystack-mytopic-NZJ5JSMVGFIE'
    end_user_role_name = 'SomeRoleName'
    parentdir = Path(__file__).parent
    budget_rules = (
      'teams:\n'
      '  \'3412821\':\n'
      '    amount: \'10\'\n'
      '    period: ANNUALLY\n'
      '    unit: USD\n'
      '    community_manager_emails:\n'
      '      - someone@example.org'
      )
    thresholds = (
      'notify_user_only: [25.0, 50.0, 80.0]\n'
      'notify_admins_too: [90.0, 100.0, 110.0]'
      )
    with patch.dict('os.environ', {
      'AWS_ACCOUNT_ID': account_id,
      'SYNAPSE_TEAM_MEMBER_LIST_ENDPOINT': endpoint,
      'NOTIFICATION_TOPIC_ARN': topic_arn,
      'BUDGET_RULES': budget_rules,
      'THRESHOLDS': thresholds,
      'END_USER_ROLE_NAME': end_user_role_name
      }):
      config = Config()

    self.assertEqual(config.account_id, account_id)
    self.assertEqual(config.synapse_team_member_list_endpoint, endpoint)
    self.assertEqual(config.notification_topic_arn, topic_arn)
    self.assertEqual(config.end_user_role_name, end_user_role_name)
    expected_budget_rules = yaml.safe_load(budget_rules)
    expected_thresholds = yaml.safe_load(thresholds)
    self.assertDictEqual(config.budget_rules, expected_budget_rules)
    self.assertDictEqual(config.thresholds, expected_thresholds)


  def test_get_env_var_present(self):
    env_var_value = 'some_value'
    env_var_key = 'SOME_ENV_VAR'
    with patch('os.getenv', MagicMock(return_value=env_var_value)) as mock:
      result = Config._get_env_var(env_var_key)
    expected = env_var_value
    self.assertEqual(result, expected)
    mock.assert_called_once_with(env_var_key)


  def test_get_env_var_missing(self):
    env_var_key = 'SOME_ENV_VAR'
    with self.assertRaises(ValueError) as context_manager:
      Config._get_env_var(env_var_key)
    expected = (
      'Lambda configuration error: '
      f'missing environment variable {env_var_key}'
    )
    self.assertEqual(str(context_manager.exception), expected)


  def test_load_yaml_happy(self):
    yaml_input = 'foo:\n  - bar'
    result = Config._load_yaml(yaml_input)
    expected = {'foo': ['bar']}
    self.assertDictEqual(result, expected)


  def test_load_yaml_invalid(self):
    yaml_input = 'foo:\n  - \'bar"'
    config_name = 'test'
    with self.assertRaises(Exception) as context_manager:
      result = Config._load_yaml(yaml_input, config_name=config_name)
    expected = f'There was an error when attempting to load {config_name}'
    self.assertTrue(str(context_manager.exception).startswith(expected))


  @patch.object(Config, "__init__", lambda x: None)
  def test_budget_rules_setter_happy(self):
    # happy path -- the setter will throw an error if the rules don't validate
    budget_rules = {
      'teams': {
        '3412821': {
          'amount': '10',
          'period': 'ANNUALLY',
          'unit': 'USD',
          'community_manager_emails': [ 'someone@example.org']
        }
      }
    }
    Config().budget_rules = budget_rules


  @patch.object(Config, "__init__", lambda x: None)
  def test_budget_rules_setter_empty(self):
    # empty test
    budget_rules = {}
    with self.assertRaises(Exception) as context_manager:
      Config().budget_rules = budget_rules
    expected = (
      f'There was a configuration validation error: '
      "{'teams': ['required field']}. "
      f'Configuration submitted: {budget_rules}'
    )
    self.assertEqual(str(context_manager.exception), expected)


  @patch.object(Config, "__init__", lambda x: None)
  def test_budget_rules_setter_empty_team(self):
    budget_rules = {
      'teams': {
        '3412821': {}
      }
    }
    with self.assertRaises(Exception) as context_manager:
      Config().budget_rules = budget_rules
    expected = (
      "[{'amount': ['required field'], "
      "'community_manager_emails': ['required field'], "
      "'period': ['required field'], "
      "'unit': ['required field']}]"
    )
    print(str(context_manager.exception))
    self.assertTrue(expected in str(context_manager.exception))

  @patch.object(Config, "__init__", lambda x: None)
  def test_budget_rules_setter_missing_manager(self):
    budget_rules = {
      'teams': {
        '3412821': {
          'amount': '10',
          'period': 'ANNUALLY',
          'unit': 'USD',
          'community_manager_emails': []
        }
      }
    }
    with self.assertRaises(Exception) as context_manager:
      Config().budget_rules = budget_rules
    expected = "{'community_manager_emails': ['min length is 1']}"
    print(str(context_manager.exception))
    self.assertTrue(expected in str(context_manager.exception))

  @patch.object(Config, "__init__", lambda x: None)
  def test_thresholds_setter_happy(self):
    thresholds = {
      'notify_user_only': [50.0],
      'notify_admins_too': [100.0]
    }
    Config().thresholds = thresholds


  @patch.object(Config, "__init__", lambda x: None)
  def test_thresholds_setter_all_empty(self):
    thresholds = {}
    with self.assertRaises(Exception) as context_manager:
      Config().thresholds = thresholds
    expected = (
      "{'notify_admins_too': ['required field'], 'notify_user_only': "
      "['required field']}"
    )
    print(str(context_manager.exception))
    self.assertTrue(expected in str(context_manager.exception))


  @patch.object(Config, "__init__", lambda x: None)
  def test_thresholds_setter_empty_list(self):
    thresholds = {
      'notify_user_only': [],
      'notify_admins_too': [100.0]
    }
    with self.assertRaises(Exception) as context_manager:
      Config().thresholds = thresholds
    expected = "{'notify_user_only': ['min length is 1']}"
    print(str(context_manager.exception))
    self.assertTrue(expected in str(context_manager.exception))
