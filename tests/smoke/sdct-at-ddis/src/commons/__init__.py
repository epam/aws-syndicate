from commons.exception import ApplicationException

RESPONSE_BAD_REQUEST_CODE = 400
RESPONSE_UNAUTHORIZED = 401
RESPONSE_FORBIDDEN_CODE = 403
RESPONSE_RESOURCE_NOT_FOUND_CODE = 404
RESPONSE_OK_CODE = 200
RESPONSE_INTERNAL_SERVER_ERROR = 500
RESPONSE_NOT_IMPLEMENTED = 501
RESPONSE_SERVICE_UNAVAILABLE_CODE = 503


def build_response(content, code=200):
    if code == RESPONSE_OK_CODE:
        return {
            'code': code,
            'body': content
        }
    raise ApplicationException(
        code=code,
        content=content
    )


def raise_error_response(code, content):
    raise ApplicationException(code=code, content=content)
