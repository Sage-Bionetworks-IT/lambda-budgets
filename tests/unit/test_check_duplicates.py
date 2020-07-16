import json
import unittest

from budget import app


class TestCheckUserDuplicates(unittest.TestCase):

  def test_check_no_duplicates(self):
    no_duplicates = {
      '1234567': ['A'],
      '8901234': ['B']
    }
    result = app.check_user_duplicates(no_duplicates)
    expected = ''
    self.assertEqual(result, expected)


  def test_check_has_duplicates(self):
    has_duplicates = {
      '1234567': ['A','B'],
      '8901234': ['B','C']
    }
    result = app.check_user_duplicates(has_duplicates)
    expected = ('Synapse user id 1234567 occurs in teams A, B\n'
      'Synapse user id 8901234 occurs in teams B, C')
    self.assertEqual(result, expected)
