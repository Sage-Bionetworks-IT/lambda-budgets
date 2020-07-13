import json
import logging

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


def lambda_handler(event, context):

    log.debug(json.dumps(event))

    return {
        "statusCode": 200
    }
