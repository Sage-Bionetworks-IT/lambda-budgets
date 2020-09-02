import json
import unittest
from unittest.mock import patch, MagicMock

from budget import app
import synapseclient


team_id_to_team_member = {
  '12345':[
      { "teamId": "12345", "member": { "ownerId": "1234567", "firstName": "Jane", "lastName": "Doe", "userName": "janedoe", "isIndividual": True}, "isAdmin": True },
       { "teamId": "12345", "member": {"ownerId": "8901234", "firstName": "John", "lastName": "Roe", "userName": "johnroe", "isIndividual": True}, "isAdmin": False}
  ],
  '67890':[
      { "teamId": "67890", "member": { "ownerId": "5678901", "firstName": "Una", "lastName": "Smith", "userName": "unasmith", "isIndividual": True}, "isAdmin": True },
      { "teamId": "67890", "member": {"ownerId": "2345678", "firstName": "Duo", "lastName": "Smith", "userName": "duosmith", "isIndividual": True}, "isAdmin": False}
  ]
}

def mock_get_team_members(team_id):
  if not team_id in team_id_to_team_member:
      raise ValueError("404 Client Error: Not Found")
  return team_id_to_team_member[team_id]

class TestGetUsers(unittest.TestCase):

  def setUp(self):
    app.configuration = MagicMock()
    app.configuration.account_id = '012345678901'

  def tearDown(self):
    app.configuration = None

  @patch('synapseclient.Synapse')
  def test_get_users(self, MockSynapse):
    MockSynapse.return_value.getTeamMembers=mock_get_team_members
    teams = ['12345']
    result = app.get_users(teams)
    expected = { '8901234': ['12345'] }
    self.assertDictEqual(result, expected)

  @patch('synapseclient.Synapse')
  def test_get_users_multiple_teams(self, MockSynapse):
    MockSynapse.return_value.getTeamMembers=mock_get_team_members
    teams = ['12345', '67890']
    result = app.get_users(teams)
    expected = { '8901234': ['12345'], '2345678': ['67890']}
    self.assertDictEqual(result, expected)

  @patch('synapseclient.Synapse')
  def test_get_users_response_error(self, MockSynapse):
    MockSynapse.return_value.getTeamMembers=mock_get_team_members
    teams = ['something_invalid']
    with self.assertRaises(ValueError):
        app.get_users(teams)
