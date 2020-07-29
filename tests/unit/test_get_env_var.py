import json
import os
import unittest
from unittest.mock import MagicMock, patch

from budget import app


class TestGetEnvVar(unittest.TestCase):
  env_var_value = 'some_value'
  env_var_key = 'SOME_ENV_VAR'

  def test_env_var_present(self):
    with patch('os.getenv', MagicMock(return_value=self.env_var_value)) as mock:
      result = app._get_env_var(self.env_var_key)
    expected = self.env_var_value
    self.assertEqual(result, expected)
    mock.assert_called_once_with(self.env_var_key)


  def test_env_var_missing(self):
    with self.assertRaises(ValueError) as context_manager:
      app._get_env_var(self.env_var_key)
    expected = (
      'Lambda configuration error: '
      f'missing environment variable {self.env_var_key}'
    )
    self.assertEqual(str(context_manager.exception), expected)
