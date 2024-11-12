from syndicate.commons.log_helper import get_logger
from syndicate.core.resources.base_resource import BaseResource
from syndicate.core.resources.helper import validate_params

_LOG = get_logger('syndicate.core.resources.dynamo_db_resource')

API_REQUIRED_PARAMS = ['schema']


class AppSyncResource(BaseResource):

    def __init__(self, appsync_conn) -> None:
        self.appsync_conn = appsync_conn

    def create_graphql_api(self, args):
        """ Create GraphQL API in pool in sub processes.

        :type args: list
        """
        return self.create_pool(self._create_graphql_api_from_meta, args, 1)

    def _create_graphql_api_from_meta(self, name, meta):
        """ Create GraphQL API table from meta description.

        :type name: str
        :type meta: dict
        """
        validate_params(name, meta, API_REQUIRED_PARAMS)
        api_id = self.appsync_conn.create_graphql_api(
            name, auth_type=meta.get('auth_type'), tags=meta.get('tags'),
            user_pool_config=meta.get('user_pool_config'),
            open_id_config=meta.get('open_id_config'),
            lambda_auth_config=meta.get('lambda_auth_config'),
            log_config=meta.get('log_config'),
            api_type=meta.get('api_type'))

        self.appsync_conn.create_schema(api_id)
        self.appsync_conn.create_data_source(api_id)
        self.appsync_conn.create_resolver(api_id)