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
from concurrent.futures import ALL_COMPLETED
from concurrent.futures.thread import ThreadPoolExecutor


class BaseResource:

    def create_pool(self, job, parameters, workers=None):
        """ Create resources in pool in sub processes.

        :param workers:
        :type parameters: iterable
        :type job: func
        """
        executor = ThreadPoolExecutor(
            workers) if workers else ThreadPoolExecutor()
        try:
            # futures = [executor.submit(func, i, kwargs) for i in args]
            futures = []
            for param_chunk in parameters:
                param_chunk['self'] = self
                futures.append(executor.submit(job, param_chunk))
            concurrent.futures.wait(futures, return_when=ALL_COMPLETED)
            responses = {}
            for future in futures:
                result = future.result()
                if result:
                    responses.update(result)
            return responses
        finally:
            executor.shutdown(wait=True)
