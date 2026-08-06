import json
from http import HTTPStatus

from commons.constants import CORS_HEADERS


def parse_body(event):
    body = event.get('body') or '{}'
    if not isinstance(body, dict):
        body = json.loads(body)
    return body


def get_authorizer_claims(event):
    return (event.get('requestContext', {})
            .get('authorizer', {})
            .get('claims', {}))


def build_response(status: HTTPStatus, body=None):
    response = {
        'statusCode': status,
        'headers': dict(CORS_HEADERS),
    }
    if body is not None:
        response['body'] = json.dumps(body)
    return response
