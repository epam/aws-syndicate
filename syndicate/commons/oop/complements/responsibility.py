from ..patterns import (
    IResponsibilityNode, IReference
)
from typing import Union, Type


def route_node(source: IResponsibilityNode,
               destination: Union[IResponsibilityNode, Type[None]]):
    """
    Function which routes a node from a subject to an object nodes,
    denoted `source` and `destination`.
    :source:IResponsibilityNode
    :destination:Union[IResponsibilityNode, Type[None]]
    :return:None
    """
    reference: IReference = getattr(source.relation, 'reference', None)
    if not isinstance(reference, IReference):
        raise NotImplementedError('Source node must contain a reference'
                                  ' instance.')
    reference.commitment = destination

