import json
import unittest
from unittest.mock import call, MagicMock, patch

import boto3
from botocore.exceptions import ClientError
from botocore.stub import Stubber, ANY

from budget import app


class TestDeleteBudgets(unittest.TestCase):

  def setUp(self):
    app.configuration = MagicMock()
    app.configuration.account_id = '012345678901'


  def tearDown(self):
    app.configuration = None


  def test_no_budgets_to_delete(self):
    no_budgets_to_remove = []
    result = app.delete_budgets(no_budgets_to_remove)
    expected = 'Budgets removed for synapse ids: none'
    self.assertEqual(result, expected)


  def test_budgets_deleted(self):
    synapse_ids = ['3406211', '3388489']
    budgets_client = boto3.client('budgets')
    with Stubber(budgets_client) as stubber:
      app.get_client = MagicMock(return_value=budgets_client)
      for synapse_id in synapse_ids:
        expected_params = {
          'AccountId': '012345678901',
          'BudgetName': app._get_budget_name(synapse_id)

        }
        stubber.add_response('delete_budget', {}, expected_params)
      result = app.delete_budgets(synapse_ids)

    expected = 'Budgets removed for synapse ids: 3406211, 3388489'
