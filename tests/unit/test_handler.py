import json
import unittest
from unittest.mock import MagicMock, patch

from budget import app


class TestHandler(unittest.TestCase):

  # This test only looks at how the success message is put together
  # for the return value. All the functions it calls have their own tests.
  def test_handler_happy_path(self):
    with patch('budget.app.Config') as config_mock, \
      patch('budget.app.get_users',
      MagicMock(return_value={})) as users_mock, \
        patch('budget.app.check_user_duplicates',
        MagicMock(return_value='')) as dupe_mock, \
      patch('budget.app.compare_budgets_and_users',
        MagicMock(return_value=([],[]))) as compare_mock, \
      patch('budget.app.create_budgets',
        MagicMock(
          return_value='Budgets created for synapse ids: 3388489')
        ) as create_mock, \
      patch('budget.app.delete_budgets',
        MagicMock(
          return_value='Budgets removed for synapse ids: 3406211')
        ) as delete_mock:
      result = app.lambda_handler({}, {})

    expected = {
      'message': (
        'Budget maker run complete; '
        'Budgets created for synapse ids: 3388489; '
        'Budgets removed for synapse ids: 3406211'
      )}
    self.assertEqual(result, expected)
    users_mock.assert_called_once()
    dupe_mock.assert_called_once()
    compare_mock.assert_called_once()
    create_mock.assert_called_once()
    delete_mock.assert_called_once()


  # Test general error handling
  def test_handler_unhappy_path(self):
    result = app.lambda_handler({}, {})
    expected = {
      'error': (
        'Lambda configuration error: missing environment variable '
        'AWS_ACCOUNT_ID'
        )
    }
    self.assertEqual(result, expected)
