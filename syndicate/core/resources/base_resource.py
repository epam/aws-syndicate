"""
    Copyright 2018 EPAM Systems, Inc.

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
"""
import concurrent
import traceback
from concurrent.futures import ALL_COMPLETED
from concurrent.futures.thread import ThreadPoolExecutor
from botocore.exceptions import ClientError, BotoCoreError

from syndicate.commons import deep_get
from syndicate.exceptions import SyndicateBaseError
from syndicate.commons.log_helper import get_logger

_LOG = get_logger(__name__)


class BaseResource:

    def create_pool(self, job, parameters, workers=None):
        """ Create resources in pool in sub processes.

        :param workers:
        :type parameters: iterable
        :type job: func
        """
        exceptions = []
        executor = ThreadPoolExecutor(
            workers) if workers else ThreadPoolExecutor()
        futures_dict = {}
        try:
            # futures = [executor.submit(func, i, kwargs) for i in args]
            futures = []
            for param_chunk in parameters:
                param_chunk['self'] = self
                future = executor.submit(job, param_chunk)
                futures.append(future)
                futures_dict[future] = param_chunk
            concurrent.futures.wait(futures, return_when=ALL_COMPLETED)
            responses = {}
            for future in futures:
                try:
                    result = future.result()
                    if result:
                        responses.update(result)
                except Exception as e:
                    param_chunk = futures_dict[future]
                    resource_name = (
                            param_chunk.get('name') or
                            deep_get(
                                param_chunk,
                                ['config', 'resource_name'],
                                'Unknown'))
                    if isinstance(e, (ClientError, BotoCoreError)):
                        exceptions.append(
                            f'When processing the resource {resource_name} {e}'
                        )
                    elif isinstance(e, SyndicateBaseError):
                        exceptions.append(
                            f'When processing the resource {resource_name} '
                            f'occurred {e.__class__.__name__} {e}'
                        )
                    else:
                        exceptions.append(
                            f'When processing the resource {resource_name} '
                            f'occurred an unexpected error '
                            f'({e.__class__.__name__}) {e}'
                        )
                    _LOG.exception(
                        f'An error occurred when processing the resource '
                        f'\'{resource_name}\'. {traceback.format_exc()}'
                    )

            return (responses, exceptions) if exceptions else responses
        finally:
            executor.shutdown(wait=True)
