from abc import abstractmethod

from commons import ApplicationException, build_response
from commons.log_helper import get_logger

_LOG = get_logger(__name__)


class AbstractLambda:

    @abstractmethod
    def validate_request(self, event) -> dict:
        """
        Validates event attributes
        :param event: lambda incoming event
        :return: dict with attribute_name in key and error_message in value
        """
        pass

    @abstractmethod
    def handle_request(self, event, context):
        """
        Inherited lambda function code
        :param event: lambda event
        :param context: lambda context
        :return:
        """
        pass

    def lambda_handler(self, event, context):
        try:
            _LOG.debug(f'Request: {event}')
            if event.get('warm_up'):
                return
            errors = self.validate_request(event=event)
            if errors:
                return build_response(code=400,
                                      content=errors)
            execution_result = self.handle_request(event=event,
                                                   context=context)
            _LOG.debug(f'Response: {execution_result}')
            return execution_result
        except ApplicationException as e:
            _LOG.error(f'Error occurred; Event: {event}; Error: {e}')
            return build_response(code=e.code,
                                  content=e.content)
        except Exception as e:
            _LOG.error(
                f'Unexpected error occurred; Event: {event}; Error: {e}')
            return build_response(code=500,
                                  content='Internal server error')
