import json
import unittest
from unittest.mock import MagicMock, patch

import boto3
from botocore.exceptions import ClientError
from botocore.stub import Stubber

from budget import app


class TestCompareBudgetsAndUsers(unittest.TestCase):

  def setUp(self):
    app.configuration = MagicMock()
    app.configuration.account_id = '012345678901'


  def tearDown(self):
    app.configuration = None


  # these are very truncated mock responses containing as few fields as possible
  mock_budget_response_1 = {
    'Budgets': [
      { 'BudgetName': 'service-catalog_3388489', 'BudgetType': 'COST', 'TimeUnit': 'ANNUALLY' }
    ]
  }
  mock_budget_response_2 = {
    'Budgets': [
      { 'BudgetName': 'service-catalog_3388489', 'BudgetType': 'COST', 'TimeUnit': 'ANNUALLY' },
      { 'BudgetName': 'service-catalog_1234567', 'BudgetType': 'COST', 'TimeUnit': 'ANNUALLY' }
    ]
  }
  mock_budget_response_3 = {
    'Budgets': [
      { 'BudgetName': 'service-catalog_3388489', 'BudgetType': 'COST', 'TimeUnit': 'ANNUALLY' },
      { 'BudgetName': 'some-non-service-catalog-budget', 'BudgetType': 'COST', 'TimeUnit': 'ANNUALLY' }
    ]
  }


  def test_no_difference(self):
    budgets_client = boto3.client('budgets')
    with Stubber(budgets_client) as stubber:
      app.get_client = MagicMock(return_value=budgets_client)
      stubber.add_response('describe_budgets', self.mock_budget_response_1)
      user_id_list = ['3388489']
      user_ids_without_budget, budgets_to_remove = app.compare_budgets_and_users(user_id_list)
      expected_without_budget = []
      expected_budgets_to_remove = []
      self.assertCountEqual(user_ids_without_budget, expected_without_budget)
      self.assertCountEqual(budgets_to_remove, expected_budgets_to_remove)


  def test_missing_user(self):
    budgets_client = boto3.client('budgets')
    with Stubber(budgets_client) as stubber:
      app.get_client = MagicMock(return_value=budgets_client)
      stubber.add_response('describe_budgets', self.mock_budget_response_1)
      user_id_list = ['3388489', '1234567']
      user_ids_without_budget, budgets_to_remove = app.compare_budgets_and_users(user_id_list)
      expected_without_budget = ['1234567']
      expected_budgets_to_remove = []
      self.assertCountEqual(user_ids_without_budget, expected_without_budget)
      self.assertCountEqual(budgets_to_remove, expected_budgets_to_remove)


  def test_too_many_budgets(self):
    budgets_client = boto3.client('budgets')
    with Stubber(budgets_client) as stubber:
      app.get_client = MagicMock(return_value=budgets_client)
      stubber.add_response('describe_budgets', self.mock_budget_response_2)
      user_id_list = ['3388489']
      user_ids_without_budget, budgets_to_remove = app.compare_budgets_and_users(user_id_list)
      expected_without_budget = []
      expected_budgets_to_remove = ['1234567']
      self.assertCountEqual(user_ids_without_budget, expected_without_budget)
      self.assertCountEqual(budgets_to_remove, expected_budgets_to_remove)

  def test_non_service_catalog_budgets_present(self):
    budgets_client = boto3.client('budgets')
    with Stubber(budgets_client) as stubber:
      app.get_client = MagicMock(return_value=budgets_client)
      # response includes a budget that uses a different naming convention
      stubber.add_response('describe_budgets', self.mock_budget_response_3)
      user_id_list = ['3388489']
      user_ids_without_budget, budgets_to_remove = app.compare_budgets_and_users(user_id_list)
      expected_without_budget = []
      # the non-service-catalog budget should not show up in this list
      expected_budgets_to_remove = []
      self.assertCountEqual(user_ids_without_budget, expected_without_budget)
      self.assertCountEqual(budgets_to_remove, expected_budgets_to_remove)
