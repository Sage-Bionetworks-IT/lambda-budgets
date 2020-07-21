import json
import unittest

from budget import app
import requests
import responses


class TestGetUsers(unittest.TestCase):

  def test_get_users(self):
    teams = ['12345']
    with responses.RequestsMock() as request_mocker:
      synapse_url = f'{app.SYNAPSE_TEAM_MEMBER_URL}/{teams[0]}'
      request_mocker.add(
        responses.GET,
        synapse_url,
        body=json.dumps({
          'totalNumberOfResults': 2,
          'results':[
            { "teamId": "12345", "member": { "ownerId": "1234567", "firstName": "Jane", "lastName": "Doe", "userName": "janedoe", "isIndividual": True}, "isAdmin": True },
            { "teamId": "12345", "member": {"ownerId": "8901234", "firstName": "John", "lastName": "Roe", "userName": "johnroe", "isIndividual": True}, "isAdmin": False}
          ]
        }),
        status=200,
        content_type='application/json'
      )
      result = app.get_users_by_team(teams)
    expected = { '8901234': ['12345'] }
    self.assertDictEqual(result, expected)


  def test_get_users_multiple_teams(self):
    teams = ['12345', '67890']
    with responses.RequestsMock() as request_mocker:
      team_id = teams[0]
      team_url_0 = f'{app.SYNAPSE_TEAM_MEMBER_URL}/{teams[0]}'
      request_mocker.add(
        responses.GET,
        team_url_0,
        body=json.dumps({
          'totalNumberOfResults': 2,
          'results':[
            { "teamId": "12345", "member": { "ownerId": "1234567", "firstName": "Jane", "lastName": "Doe", "userName": "janedoe", "isIndividual": True}, "isAdmin": True },
            { "teamId": "12345", "member": {"ownerId": "8901234", "firstName": "John", "lastName": "Roe", "userName": "johnroe", "isIndividual": True}, "isAdmin": False}
          ]
        }),
        status=200,
        content_type='application/json'
      )
      team_url_1 = f'{app.SYNAPSE_TEAM_MEMBER_URL}/{teams[1]}'
      request_mocker.add(
        responses.GET,
        team_url_1,
        body=json.dumps({
          'totalNumberOfResults': 2,
          'results':[
            { "teamId": "67890", "member": { "ownerId": "5678901", "firstName": "Una", "lastName": "Smith", "userName": "unasmith", "isIndividual": True}, "isAdmin": True },
            { "teamId": "67890", "member": {"ownerId": "2345678", "firstName": "Duo", "lastName": "Smith", "userName": "duosmith", "isIndividual": True}, "isAdmin": False}
          ]
        }),
        status=200,
        content_type='application/json'
      )
      result = app.get_users_by_team(teams)
    expected = { '8901234': ['12345'], '2345678': ['67890']}
    self.assertDictEqual(result, expected)


  def test_get_users_response_error(self):
    teams = ['something_invalid']
    with responses.RequestsMock() as request_mocker, \
      self.assertRaises(requests.exceptions.HTTPError) as exception_manager:
      team_members_url = f'{app.SYNAPSE_TEAM_MEMBER_URL}/{teams[0]}'
      request_mocker.add(
        responses.GET,
        team_members_url,
        status=404)
      result = app.get_users_by_team(teams)
    expected_error = f'404 Client Error: Not Found for url: {team_members_url}'
    self.assertEqual(str(exception_manager.exception), expected_error)
