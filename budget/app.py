import json
import logging
import os
import traceback

import boto3
from botocore.exceptions import ClientError
import requests

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

# TEAM_BUDGET_RULES contains configuration for creating a budget for each user
# on a team. For example, the dictionary at TEAM_BUDGET_RULES['teams']['3412821']
# contains a value of '10' for amount. For each user in that team, a budget will
# be created for that user's activity only, with a limit of that amount.
TEAM_BUDGET_RULES = {
  'teams': {
    '3412821': {
      #'amount': '2000',
      'amount': '10',
      'period': 'ANNUALLY',
      'community_manager_emails': ['tess.thyer@sagebase.org']
    }
  },
  'thresholds': {
    'notify_user_only': [25.0, 50.0, 80.0],
    'notify_admins_too': [90.0, 100.0, 110.0]
  }
}

BUDGET_NAME_PREFIX = 'service-catalog_'

configuration = {}


def _get_env_var(name):
  value = os.getenv(name)
  if not value:
    raise ValueError(('Lambda configuration error: '
      f'missing environment variable {name}'))
  return value


def _set_configuration():
  configuration['account_id'] = _get_env_var('AWS_ACCOUNT_ID')
  configuration['synapse_team_member_list_endpoint'] = _get_env_var('SYNAPSE_TEAM_MEMBER_LIST_ENDPOINT')
  configuration['notification_topic_arn'] = _get_env_var('NOTIFICATION_TOPIC_ARN')


def _get_synapse_team_member_url(team_id):
  return f'{configuration["synapse_team_member_list_endpoint"]}/{team_id}'


def get_client(service):
  return boto3.client(service)


def get_users(teams):
  '''Get users from synapse teams

  Returns a dictionary of users with a list of their team memberships
  '''
  teams_by_user_id = {}
  for team_id in teams:
    synapse_url = _get_synapse_team_member_url(team_id)
    response = requests.get(synapse_url)
    if response.ok:
      results = json.loads(response.text)['results']
      user_ids = [
        result['member']['ownerId']
        for result in results if not result['isAdmin']
      ]
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


def compare_budgets_and_users(users):
  '''Finds users who lack a budget

  This checks budget names against the user list,
  returning a list of user ids that need a budget to be made
  '''
  budgets_client = get_client('budgets')

  # get budgets
  budgets = budgets_client.describe_budgets(
    AccountId=configuration['account_id']
    ).get('Budgets')

  # get just the Service Catalog budget names
  service_catalog_budget_names = []
  if budgets:
    service_catalog_budget_names = [
      budget['BudgetName'] for budget in budgets
      if budget['BudgetName'].startswith(BUDGET_NAME_PREFIX)
    ]
  log.debug(f'Service Catalog budget names: {service_catalog_budget_names}')

  # derive user ids from budget names
  service_catalog_budgets_user_ids = set([
    budget_name.split(BUDGET_NAME_PREFIX)[1]
    for budget_name in service_catalog_budget_names
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
  log.debug(f'Creating budget for synapse user {synapse_id}, member of team {team}')

  team_budget_rules = TEAM_BUDGET_RULES.get('teams').get(team)
  if not team_budget_rules:
    raise ValueError(f'No budget rules available for team {team}')
  budget_amount = team_budget_rules['amount']
  budget_period = team_budget_rules['period']
  budget = {
    'BudgetName': f'{BUDGET_NAME_PREFIX}{synapse_id}',
    'BudgetLimit': {
      'Amount': budget_amount,
      'Unit': 'USD'
    },
    'CostFilters': {
      'TagKeyValue': [
        (
          'aws:servicecatalog:provisioningPrincipalArn$arn:aws:sts::'
          f'{configuration["account_id"]}:assumed-role/ServiceCatalogEndusers/{synapse_id}'
        )
      ]
    },
    'CostTypes': {
      'IncludeRefund': False,
      'IncludeCredit': False
    },
    'TimeUnit': budget_period,
    'BudgetType': 'COST'
  }
  budgets_client = get_client('budgets')
  return budgets_client.create_budget(
    AccountId=configuration['account_id'],
    Budget=budget
    )


def _create_budget_notification(synapse_id, threshold, admin_emails=None):
  '''Creates a notification rule when the budget crosses a particular threshold.

  May have multiple recipients. User notifications are sent through SNS
  in order to send email to Synapse addresses, which cannot receive email
  unless sent through the Synapse system, but emails to administrators can
  be sent directly.
  '''
  budgets_client = get_client('budgets')
  budget_name = f'{BUDGET_NAME_PREFIX}{synapse_id}'
  subscribers = []
  # add admin subscription through email if admin_emails were included
  if admin_emails:
    subscribers = [{
      'SubscriptionType': 'EMAIL',
      'Address': address
    } for address in admin_emails]
  # add sns subscription for the user
  subscribers.append({
    'SubscriptionType': 'SNS',
    'Address': configuration['notification_topic_arn']
    })

  return budgets_client.create_notification(
      AccountId=configuration['account_id'],
      BudgetName=budget_name,
      Notification={
          'NotificationType': 'ACTUAL',
          'ComparisonOperator': 'GREATER_THAN',
          'Threshold': threshold,
          'ThresholdType': 'PERCENTAGE',
          'NotificationState': 'ALARM'
      },
      Subscribers=subscribers
  )


def create_budget_notifications(synapse_id, team):
  '''Creates notifications for a particular budget'''
  budget_name = f'{BUDGET_NAME_PREFIX}{synapse_id}'
  thresholds = TEAM_BUDGET_RULES['thresholds']

  for threshold in thresholds['notify_user_only']:
    _create_budget_notification(
      synapse_id,
      threshold
    )

  for threshold in thresholds['notify_admins_too']:
    _create_budget_notification(
      synapse_id,
      threshold,
      admin_emails=TEAM_BUDGET_RULES['teams'][team]['community_manager_emails']
    )


def create_budgets(user_ids_without_budget, teams_by_user_id):
  '''Creates a budget for each synapse id'''
  new_budgets_created = []
  for synapse_id in user_ids_without_budget:
    team = teams_by_user_id[synapse_id][0]
    create_budget(synapse_id, team)
    create_budget_notifications(synapse_id, team)
    new_budgets_created.append(synapse_id)

  return (
    'Budgets created for synapse ids: '
    f'{"none" if not new_budgets_created else ", ".join(new_budgets_created)}'
  )


def delete_budgets(synapse_ids):
  # TODO implement
  budgets_removed = []
  return ('Budgets removed for synapse_ids: '
    f'{"none" if not budgets_removed else ", ".join(budgets_removed)}'
  )


def lambda_handler(event, context):
  '''Lambda event handler'''
  log.debug('Event received: ' + json.dumps(event))

  try:
    _set_configuration()
    # TODO validate TEAM_BUDGET_RULES schema here

    # get users
    teams = TEAM_BUDGET_RULES.get('teams').keys()
    teams_by_user_id = get_users(teams)

    # verify that no users appear in multiple teams
    duplicates = check_user_duplicates(teams_by_user_id)
    if duplicates:
      log.warn(f'One or more duplicate team memberships was found.\n{duplicates}')

    # check which user ids need a budget, and which budgets should be removed
    user_ids_without_budget, budgets_to_remove = compare_budgets_and_users(
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
    log.error(e, exc_info=True)

    return {
      'error': str(e)
    }
