from . import AbstractBuilder
from .. import IRelation, IReference
from .. import (
    IResponsibilityNode, BlackBoxResponsibilityNode
)

from functools import wraps, singledispatchmethod
from typing import Callable
from types import FunctionType
from collections import deque


class CurriedFunctionBuilder(AbstractBuilder):

    def _reset(self):
        """
        Resets a builder to empty body and retrieve attributes.
        """
        self._body = None
        self._retrieve = lambda args: args

    @singledispatchmethod
    def attach(self, part):
        raise NotImplementedError

    @attach.register
    def _attach(self, part: FunctionType):
        """
        Attaches single persistent function to the body.
        """
        self._body = part

    @attach.register
    def _attach(self, part: deque):
        """
        Attaches deque of functions to the body, which shifts a queue for each
        invocation, compelling to cycle through each outsourced body.
        """
        def fetch(source: deque):
            function = source.popleft() if bool(source) else None
            if not isinstance(function, Callable):
                function = lambda *args, **kwargs: None
            return function

        initial = fetch(part)
        part.appendleft(initial)

        @wraps(initial)
        def wrapper(*args, **kwargs):
            outsourced = fetch(part)
            output = outsourced(*args, **kwargs)
            part.append(outsourced)
            return output

        self.attach(wrapper)

    def pre(self, part):
        self.attach(self._pre(part) if self._body else part)

    def post(self, part):
        self.attach(self._post(part) if self._body else part)

    def retrieve(self, part):
        """
        Sets up a return policy of a curried function.
        """
        if not isinstance(part, Callable):
            raise TypeError('A retrieve policy of a function must be callable.')
        self._retrieve = part

    @property
    def product(self):
        _ = super(self.__class__, self).product
        retrieve = self._retrieve
        body = self._post(retrieve)
        self._reset()
        return body

    def _pre(self, part):
        return self._wrap(lambda target, *args, **kwargs: target(
            part(*args, **kwargs)
        ))

    def _post(self, part):
        return self._wrap(lambda target, *args, **kwargs: part(
            target(*args, **kwargs)
        ))

    def _wrap(self, composition):
        target = self._body

        @wraps(target)
        def wrapper(*args, **kwargs):
            return composition(target, *args, **kwargs)
        return wrapper


class ResponsibilityNodeBuilder(AbstractBuilder):

    """
    A concrete Builder class, which provides behaviour aimed at
    producing a non-computable ResponsibilityNode.
    """

    def _reset(self):
        self._node = None
        self._relation = None
        self._reference = None

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


class BlackBoxResponsibilityNodeBuilder(AbstractBuilder):
    """
    A concrete Builder class, which provides behaviour for
    producing a outsourced, black-box computable ResponsibilityNode, based
    on a curried function builder.
    """

    def _reset(self):
        self._node = None
        self._builder = None
        self._deque = None

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
        if not self._deque:
            self._deque = deque()
        self._deque.append(part)

    @attach.register
    def _attach(self, part: CurriedFunctionBuilder):
        """
        Attaches a currying function builder, for an eminent product generation,
        deemed as an outsourced black-box computation.
        :part:CurriedFunctionBuilder
        :return:None
        """
        self._builder = part

    @property
    def product(self):
        """
        Returns a black-box responsibility node, attaching
        the outsourced computation to the curried function builder,
        providing an executable box of a node.
        :returns:BlackBoxResponsibilityNode
        """
        _ = super(self.__class__, self).product
        node, builder, _deque = self._node, self._builder, self._deque
        builder.attach(_deque if len(_deque) > 1 else _deque.pop())
        node.box = builder.product
        self._reset()
        return node
