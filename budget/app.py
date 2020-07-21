import json
import logging

import boto3
from botocore.exceptions import ClientError
import requests

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

# TODO configure this URL?
SYNAPSE_TEAM_MEMBER_URL = 'https://repo-prod.prod.sagebase.org/repo/v1/teamMembers'

# TODO pull this config from S3?
USER_BUDGET_BY_TEAM = {
  '12345': {
    'amount': 2000,
    'period': 'annual'
  },
  '67890': {
    'amount': 100,
    'period': 'annual'
  }
}


def get_client(service):
  return boto3.client(service)


def get_users_by_team(teams):
  '''Get users from synapse teams

  Returns a dictionary of users with a list of their team memberships
  '''
  teams_by_user_id = {}
  for team_id in teams:
    synapse_url = f'{SYNAPSE_TEAM_MEMBER_URL}/{team_id}'
    response = requests.get(synapse_url)
    if response.ok:
      results = json.loads(response.text)['results']
      user_ids = [result['member']['ownerId'] for result in results if not result['isAdmin']]
    else:
      response.raise_for_status()
    for user_id in user_ids:
      if user_id in teams_by_user_id:
        teams_by_user_id[user_id].append(team_id)
      else:
        teams_by_user_id[user_id] = [team_id]
  return teams_by_user_id


def check_user_duplicates(teams_by_user_id):
  '''Verify that no users occur in multiple teams'''

  duplicates = {user_id:team_memberships
    for (user_id,team_memberships) in teams_by_user_id.items()
    if len(team_memberships) > 1
  }

  if not duplicates:
    return ''  # return an empty message if there are no duplicates
  else:
    return '\n'.join([
      f'Synapse user id {user_id} occurs in teams {", ".join(team_memberships)}'
      for (user_id, team_memberships) in duplicates.items()
    ])


def compare_budgets_and_users(account_id, users):
  '''Finds users who lack a budget

  This checks budget names, which will use the format
  f'service-catalog_{synapse_id}', against the user list,
  returning a list of user ids that need a budget to be made
  '''
  budgets_client = get_client('budgets')

  # get budgets
  budgets = budgets_client.describe_budgets(
    AccountId=account_id
    ).get('Budgets')

  # get just the budget names
  service_catalog_budget_names = [
    budget['BudgetName'] for budget in budgets
    if budget['BudgetName'].startswith('service-catalog_')
  ]

  # derive user ids from budget names
  service_catalog_budgets_user_ids = set([
    budget_name.split('_')[1] for budget_name in service_catalog_budget_names
  ])

  users = set(users)

  # check for differences in ids found in budgets names and user ids from team
  user_ids_without_budget = []
  budgets_to_remove = []
  if service_catalog_budgets_user_ids != users:
    user_ids_without_budget = list(users - service_catalog_budgets_user_ids)
    budgets_to_remove = list(service_catalog_budgets_user_ids - users)

  return user_ids_without_budget, budgets_to_remove


def create_budget(synapse_id, team):
  '''Creates an AWS budget for a synapse user id'''
  # TODO implement
  log.info('Placeholder -- this will make a budget')


def create_budgets(user_ids_without_budget, teams_by_user_id):
  '''Creates a budget for each synapse id'''
  new_budgets_created = []
  for synapse_id in user_ids_without_budget:
    team = teams_by_user_id[synapse_id][0]
    create_budget(synapse_id, team)
    new_budgets_created.append(synapse_id)

  return f'Budgets created: {"none" if not new_budgets_created else ", ".join(new_budgets_created)}'


def delete_budgets(synapse_ids):
  # TODO implement
  budgets_removed = []
  return f'Budgets removed for synapse_ids: {"none" if not budgets_removed else ", ".join(budgets_removed)}'


def lambda_handler(event, context):
  '''Lambda event handler'''
  log.debug('Event received: ' + json.dumps(event))

  try:
    # get users
    teams = []
    teams_by_user_id = get_users_by_team(teams)

    # verify that no users appear in multiple teams
    duplicates = check_user_duplicates(teams_by_user_id)
    if duplicates:
      log.warn(f'One or more duplicate team memberships was found.\n{duplicates}')

    # check which user ids need a budget, and which budgets should be removed
    account_id = '465877038949'  # TODO make account_id configurable
    user_ids_without_budget, budgets_to_remove = compare_budgets_and_users(
      account_id,
      teams_by_user_id.keys()
    )

    # create budgets, if applicable
    budgets_created_message = create_budgets(user_ids_without_budget, teams_by_user_id)

    # remove budgets, if applicable
    budgets_removed_message = delete_budgets(budgets_to_remove)

    success_message = 'Budget maker run complete'
    if budgets_created_message:
      success_message = f'{success_message}; {budgets_created_message}'
    if budgets_removed_message:
      success_message = f'{success_message}; {budgets_removed_message}'

    log.info(success_message)

    return {
      'message': success_message
    }

  except Exception as e:
    failure_message = f'Error: {e}'

    log.error(failure_message)

    return {
      'error': failure_message
    }
