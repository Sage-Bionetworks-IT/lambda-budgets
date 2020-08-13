import json
import unittest
from unittest.mock import call, MagicMock, patch

import boto3
from botocore.exceptions import ClientError
from botocore.stub import Stubber, ANY

from budget import app


class TestCreateBudgets(unittest.TestCase):

  def setUp(self):
    app.configuration = MagicMock()
    app.configuration.account_id = '012345678901'


  def tearDown(self):
    app.configuration = None


  def test_create_budgets_no_new_users(self):
    no_new_users = []
    teams_by_user_id = {} # this doesn't matter if there are no new users
    result = app.create_budgets(no_new_users, teams_by_user_id)
    # if there are no new users, we expect a message indicating that no
    # new budgets were created
    expected = 'Budgets created for synapse ids: none'
    self.assertEqual(result, expected)


  @patch('budget.app.create_budget', MagicMock(return_value={}))
  @patch('budget.app.create_budget_notifications', MagicMock(return_value={}))
  def test_create_budgets_some_users(self):
    app.configuration.budget_rules = {'teams': {'12345': {}}}
    new_users = ['3406211', '3388489']
    teams_by_user_id = {'3406211': ['12345'], '3388489': ['12345']}
    result = app.create_budgets(new_users, teams_by_user_id)
    # if there are new users, we expect a message that budgets were
    # created for each of them
    expected = 'Budgets created for synapse ids: 3406211, 3388489'
    self.assertEqual(result, expected)


  def test_create_budget(self):
    app.configuration.budget_rules = {
      'teams':{'12345': {'amount': '100','period': 'ANNUALLY'}}
    }
    app.configuration.end_user_role_name = 'ServiceCatalogEndusers'
    synapse_id = '3388489'
    team = '12345'
    budgets_client = boto3.client('budgets')
    with Stubber(budgets_client) as stubber:
      app.get_client = MagicMock(return_value=budgets_client)
      expected_params = {
        'AccountId': '012345678901',
        'Budget': {
          'BudgetName': 'service-catalog_3388489',
          'BudgetLimit': {
            'Amount': '100',
            'Unit': 'USD'
          },
          'CostFilters': {
            'TagKeyValue': [
              (
                'aws:servicecatalog:provisioningPrincipalArn$arn:aws:sts::'
                '012345678901:assumed-role/ServiceCatalogEndusers/3388489'
              )
            ]
          },
          'CostTypes': {
            'IncludeRefund': False,
            'IncludeCredit': False
          },
          'TimeUnit': 'ANNUALLY',
          'BudgetType': 'COST'
        }
      }
      # verify that the boto3 client will be called with the expected values
      stubber.add_response('create_budget', {}, expected_params)
      result = app.create_budget(synapse_id, team)
      expected = {}
      self.assertEqual(result, expected)


  def test_create_budget_no_team_rules(self):
    app.configuration.budget_rules = {
      'teams': {
        '12345': {
          'amount': '100',
          'period': 'ANNUALLY',
          'community_manager_emails': []
        }
      }
    }
    synapse_id = '3388489'
    team = 'foo'
    with self.assertRaises(ValueError) as context_manager:
      app.create_budget(synapse_id, team)
    expected_error = 'No budget rules available for team foo'
    self.assertEqual(str(context_manager.exception), expected_error)


  def test_create_budget_notifications_makes_expected_call_types(self):
    app.configuration.budget_rules = {
      'teams': {
        '12345': {
          'amount': '100',
          'period': 'ANNUALLY',
          'community_manager_emails': []
        }
      }
    }
    app.configuration.thresholds = {
      'notify_user_only': [25.0, 50.0, 80.0],
      'notify_admins_too': [90.0, 100.0, 110.0]
    }

    synapse_id = '3388489'
    team = '12345'
    with patch('budget.app._create_budget_notification') as mock:
      app.create_budget_notifications(synapse_id, team)
    expected = [
      call('3388489', 25.0),
      call('3388489', 50.0),
      call('3388489', 80.0),
      call('3388489', 90.0, admin_emails=[]),
      call('3388489', 100.0, admin_emails=[]),
      call('3388489', 110.0, admin_emails=[])
    ]
    self.assertCountEqual(mock.mock_calls, expected)


  def test_create_budget_notification_user_only(self):
    fake_topic_arn = 'arn:aws:sns:us-east-1:123456789012:mystack-mytopic-NZJ5JSMVGFIE'
    app.configuration.notification_topic_arn = fake_topic_arn
    budgets_client = boto3.client('budgets')

    with Stubber(budgets_client) as stubber:
      app.get_client = MagicMock(return_value=budgets_client)
      # user only
      expected_params = {
        'AccountId': '012345678901',
        'BudgetName': 'service-catalog_3388489',
        'Notification': {
            'NotificationType': 'ACTUAL',
            'ComparisonOperator': 'GREATER_THAN',
            'Threshold': 25.0,
            'ThresholdType': 'PERCENTAGE',
            'NotificationState': 'ALARM'
        },
        'Subscribers': [{
          'SubscriptionType': 'SNS',
          'Address': fake_topic_arn
        }]
      }
      # verify that the boto3 client will be called with the expected values
      stubber.add_response('create_notification', {}, expected_params)
      synapse_id = '3388489'
      threshold = 25.0
      result = app._create_budget_notification(synapse_id, threshold)
      expected = {}
      self.assertEqual(result, expected)
      # now with admins
      fake_admin_email = 'jane.doe@sagebase.org'
      expected_params['Subscribers'].insert(0, {
          'SubscriptionType': 'EMAIL',
          'Address': fake_admin_email
        })
      stubber.add_response('create_notification', {}, expected_params)
      result = app._create_budget_notification(synapse_id, threshold, admin_emails=[fake_admin_email])
      expected = {}
      self.assertEqual(result, expected)
