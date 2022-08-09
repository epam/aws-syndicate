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

from ..patterns import (
    ISource, IBuilder, CurriedFunctionBuilder
)
from typing import Callable, Union, Type, Iterable, Any
from functools import singledispatch
from types import FunctionType


def produce_output_taped_builder(
    source: ISource, builder: CurriedFunctionBuilder
):
    """
    A function which produces an output taping function, comprised
    into a curried builder.
    :source:ISource
    :builder:CurriedFunctionBuilder
    :return:CurriedFunctionBuilder
    """
    builder.post(lambda args: (source.put(args), args)[-1])
    return builder


def produce_internally_taped_builder(source: ISource):
    """
    A function which produces an internally taped function, comprised into
    a curried builder.
    :source:ISource
    :return:CurriedFunctionBuilder
    """
    builder = CurriedFunctionBuilder()
    builder.attach(lambda *args, **kwargs: iter(source.get, None))
    return builder


def produce_condition_builder(determinant: Union[FunctionType, Exception],
                              action: Callable, builder: CurriedFunctionBuilder
                              ) -> CurriedFunctionBuilder:
    """
    A function which produces a condition handling builder, attaching a
    respective action for a determinant of the aforementioned condition.
    :determinant: Union[FunctionType, Exception]
    :action: Callable
    :builder: CurriedFunctionBuilder
    :return: CurriedFunctionBuilder
    """
    builder.condition(determinant, action)
    return builder


def produce_handled_internally_taped_builder(
        source: ISource, determinant: Union[FunctionType, Exception],
        action: Callable
) -> CurriedFunctionBuilder:
    """
    Produces a deterministically handling function, which is internally
    taped.
    :source:ISource
    :return:CurriedFunctionBuilder
    """
    taped = produce_internally_taped_builder(source)
    return produce_condition_builder(determinant, action, taped)


def produce_filter_builder(
    condition: Callable, extraction: Callable, unwrap: Callable, wrap: Callable,
    builder: Union[CurriedFunctionBuilder, Type[None]] = None
):
    """
    Function which produces a builder, which has been curried with an underlying
    filtering attachments.
    :condition: Callable
    :extract: Callable
    :unwrap: Callable
    :wrap: Callable
    :builder: Union[CurriedFunctionBuilder, Type[None]] = None
    :return: CurriedFunctionBuilder
    """

    builder = builder or CurriedFunctionBuilder()

    builder.attach(condition)
    builder.pre(extraction)
    condition = builder.product

    builder.attach(unwrap)
    builder.post(produce_underlying_filter(condition))
    builder.post(wrap)
    return builder


def produce_underlying_filter(condition):
    """
    Produces a lambda filtering function, based on a condition.
    :return:Callable
    """
    return lambda data: filter(condition, data)

@singledispatch
def produce_function(source):
    raise NotImplementedError

@produce_function.register
def _produce_function(source: IBuilder) -> Any:
    """
    Produces a function out of IBuilder.
    :return: Any
    """
    return source.product
