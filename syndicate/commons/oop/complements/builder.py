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


from ..patterns import CurriedFunctionBuilder


def produce_filter_function(condition, extraction, unwrap, encapsulate):

    builder = CurriedFunctionBuilder()

    builder.attach(condition)
    builder.pre(extraction)
    condition = builder.product

    builder.attach(unwrap)
    builder.post(produce_underlying_filter(condition))
    builder.post(encapsulate)
    return builder.product


def produce_underlying_filter(condition):
    return lambda data: filter(condition, data)
