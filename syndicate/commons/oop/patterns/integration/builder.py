from .. import (
    IRelation, IReference, IBuilder,
    IResponsibilityNode, AbstractBuilder,
    BlackBoxResponsibilityNode,
    CurriedFunctionBuilder
)

from ...complements import route_node

from functools import singledispatchmethod, partial
from types import FunctionType

from typing import Union, Type


class ResponsibilityNodeBuilder(AbstractBuilder):

    """
    A concrete Builder class, which provides behaviour aimed at
    producing a non-computable ResponsibilityNode.
    """

    def _reset(self):
        self._node: Union[IResponsibilityNode, Type[None]] = None
        self._relation: Union[IRelation, Type[None]] = None
        self._reference: Union[IReference, Type[None]] = None

    @singledispatchmethod
    def attach(self, part):
        raise NotImplementedError

    @attach.register
    def _attach(self, part: IResponsibilityNode):
        """
        Attaches a responsibility node to the builder.
        :part:IResponsibility
        :return:None
        """
        self._node = part

    @attach.register
    def _attach(self, part: IRelation):
        """
        Attaches a relation complement of the node.
        :part:IRelation
        :return:None
        """
        self._relation = part

    @attach.register
    def _attach(self, part: IReference):
        """
        Attaches a reference node to the builder, given commitment
        is either None or an instance of a ResponsibilityNode.
        :part:IResponsibility
        :return:None
        """
        if not any((
            part.commitment is None,
            isinstance(part.commitment, IResponsibilityNode)
        )):
            raise NotImplementedError('Reference commitment must be an instance'
                                      'of IResponsibilityNode or NoneType.')
        self._reference = part

    @property
    def product(self):
        """
        Returns a simple non-computable ResponsibilityNode, having
        assigned the reference to the relation and subsequently complemented
        the pending node with the aforementioned relation.
        :returns:IResponsibilityNode
        """
        _ = super(self.__class__, self).product
        node, relation, reference = self._node, self._relation, self._reference
        relation.reference = reference
        node.relation = relation
        self._reset()
        return node


class BlackBoxNodeResponsibilityBuilder(AbstractBuilder):
    """
    A concrete Builder class, which provides behaviour for
    producing an outsourced, black-box computable ResponsibilityNode.
    """

    def _reset(self):
        self._node = None
        self._builder = None

    @singledispatchmethod
    def attach(self, part):
        raise NotImplementedError

    @attach.register
    def _attach(self, part: BlackBoxResponsibilityNode):
        """
        Attaches a black-box responsibility node to the builder.
        :part:BlackBoxResponsibilityNode
        :return:None
        """
        self._node = part

    @attach.register
    def _attach(self, part: FunctionType):
        """
        Attaches a function to a deque of continues delegation.
        :part:FunctionType
        :return:None
        """
        if not self._builder:
            raise NotImplementedError('Function attachment could proceed only'
                                      ' after a builder has been assigned.')
        self._builder.attach(part)

    @attach.register
    def _attach(self, part: IBuilder):
        """
        Attaches a function builder, for an eminent product generation,
         deemed as an outsourced black-box computation.
        :part:IBuilder
        :return:None
        """
        self._builder = part

    @property
    def product(self) -> BlackBoxResponsibilityNode:
        """
        Returns a black-box responsibility node, attaching
        the outsourced computation to the lazy evaluation builder,
        providing an executable box of a node.
        :return:BlackBoxResponsibilityNode
        """
        _ = super(self.__class__, self).product
        node, builder = self._node, self._builder
        node.box = builder.product
        self._reset()
        return node


class DetachedResponsibilityNodeRoutingBuilder(AbstractBuilder):
    """
    A concrete Builder class, which provides behaviour for
    detached demand routing behaviour of a black box responsibility
    `source` node, using a curried function builder. `Destination` node,
    defaults to None, given one has not been given.
    """

    def _reset(self):
        self._source: Union[BlackBoxResponsibilityNode, Type[None]] = None
        self._curring: Union[CurriedFunctionBuilder, Type[None]] = None
        self._condition: Union[FunctionType, Type[None]] = None

    @singledispatchmethod
    def attach(self, part):
        raise NotImplementedError

    @attach.register
    def _attach(self, part: CurriedFunctionBuilder):
        """
        Attaches a curring function builder, meant to wrap
        the routing invocation condition.
        :part:CurriedFunctionBuilder
        :return:None
        """
        self._curring = part

    @attach.register
    def _attach(self, part: BlackBoxResponsibilityNode):
        """
        Attaches an assumed `source` responsibility node,
        given one has not been previously assigned. Otherwise,
        sets up an optional `destination` node.
        :part:BlackBoxResponsibilityNode
        :return:None
        """
        if not self._source:
            self._source = part
        else:
            self._destination = part

    @attach.register
    def _attach(self, part: IResponsibilityNode):
        """
        Attaches an optional `destination` responsibility node.
        :part:IResponsibilityNode
        :return:None
        """
        self._destination = part

    @attach.register
    def _attach(self, part: FunctionType):
        """
        Attaches a conditional routing demand based on a function, given
        that the curring builder has been assigned.
        :part:FunctionType
        :return:None
        """
        if not self._curring:
            raise NotImplementedError('Functional condition attachment could '
                                      'proceed only after a curried builder '
                                      'has been assigned.')
        message = 'Functional condition attachment could ' \
                  'proceed only after a curried builder ' \
                  'has been assigned.'
        self._condition(determinant=part, error_message=message)

    @attach.register
    def _attach(self, part: Exception):
        """
        Attaches a conditional routing demand based on an Exception, given
        that the curring builder has been assigned.
        :part:Exception
        :return:None
        """
        message = 'Exceptional condition attachment could '\
                  'proceed only after a curried builder '\
                  'has been assigned.'
        self._condition(determinant=part, error_message=message)

    def _condition(self, determinant: Union[Exception, FunctionType],
                   error_message: str):
        """
        General condition attachment to a curried function builder,
        given one has been previously assigned.
        :determinant:Union[Exception, FunctionType]
        :error_message:str
        :return: None
        """
        if not self._curring:
            raise NotImplementedError(error_message)
        curring = self._curring
        self._condition = partial(curring.condition, determinant=determinant)

    @property
    def product(self) -> BlackBoxResponsibilityNode:
        """
        Returns a black-box responsibility node, which attaching
        the outsourced computation to the lazy evaluation builder,
        providing an executable box of a node.
        :return: BlackBoxResponsibilityNode
        """
        _ = super(self.__class__, self).product
        source, curring = self._source, self._curring
        condition = self._condition
        destination = getattr(self, '_destination', None)

        # Retrieves the black-box function
        box = source.box

        # Starts off demand routing, by attaching the core function
        curring.attach(box)

        # Attaches the pre-bound demanded condition with a routing action
        # as a fail-safe consequence, returning the incoming data
        condition(
            action=lambda data: (route_node(source, destination), data)[-1]
        )
        # Retrieves route-on-demand black box
        box = curring.product
        # Attaches the wrapped box execution to the source
        source.box = box
        self._reset()
        return source
