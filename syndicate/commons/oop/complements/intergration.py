
from ..patterns import (
    ISource, BlackBoxResponsibilityNode, IResponsibilityNode,
    CurriedFunctionBuilder
)

from . import (
    route_node, produce_function, produce_internally_taped_builder
)

from typing import Union, Type


def produce_boxed_routing_builder(
        source: BlackBoxResponsibilityNode, destination: IResponsibilityNode,
        builder: Union[CurriedFunctionBuilder, Type[None]] = None
):
    """
    Produces a builder, which maintains a function, which routes
    source node to the destination one, invoking `route_node` function,
    and returns the incoming data, adhering to the signature of the
    IResponsibility node.
    :source: BlackBoxResponsibilityNode
    :destination: IResponsibilityNode
    :builder: Union[CurriedFunctionBuilder, Type[None]] = None
    :return: CurriedFunctionBuilder
    """
    builder = builder or CurriedFunctionBuilder()
    builder.attach(lambda data: (route_node(source, destination), data)[-1])
    return builder


def produce_internally_taped_node(node: BlackBoxResponsibilityNode,
                                  source: ISource):
    """
    A function producing a black boxed responsibility node,
    input of which is internally based on a source tape.
    :node: BlackBoxResponsibilityNode
    :source: ISource
    :return: BlackBoxResponsibilityNode
    """
    node.box = produce_function(produce_internally_taped_builder(source))
    return node

