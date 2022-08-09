from . import AbstractBuilder
from .. import ISource

from functools import wraps, singledispatchmethod
from typing import Callable, Dict, Tuple, Any, Union, Type
from types import FunctionType


class CurriedFunctionBuilder(AbstractBuilder):
    """
    A concrete Builder class, which provides behaviour for
    functional curring, by providing the following methods,
    which define a `body`.

    Attributes:
        - body:Union[Callable, Type[None]]: body of the curried function.

    Public methods:
        - attach(self, part:FunctionType): Attaches the body of a function.
        - retrieve(self, part:FunctionType): Attaches the body of a function.
        - pre(self, part:Callable): Attaches a function pre-computing payload.
        - post(self, part:Callable): Attaches a decorator payload.
        - condition(self, determinant:Exception, action:Callable):
            Attaches an exception-based condition, which invokes an
            action, given the exception is to arise.
        - condition(self, determinant:FunctionType, action:Callable):
            Attaches a function based condition, which invokes an
            action, given the is not True.
    Properties:
        - product:Callable: a curried result of a functional composition,
        which raises the NotImplementedError, under the assumption that
        no `body` function has been assigned.
    """
    def _reset(self):
        """
        Resets a builder to an empty body.
        """
        self._body: Union[Callable, Type[None]] = None

    @singledispatchmethod
    def attach(self, part):
        raise NotImplementedError

    @attach.register
    def _attach(self, part: FunctionType):
        """
        Attaches single persistent function to the body.
        :part:FunctionType
        :returns:None
        """
        self._body = part

    def pre(self, part: Callable):
        """
        Attaches a prepended body function, given one has been
        previously assigned, otherwise is set up as the body.
        :part:Callable
        :returns:None
        """
        self.attach(self._pre(part) if self._body else part)

    def post(self, part):
        """
        Attaches a wrapper around a body function, given one has been
        previously assigned, otherwise is set up as the body.
        :part:Callable
        :returns:None
        """
        self.attach(self._post(part) if self._body else part)

    @singledispatchmethod
    def condition(self, determinant, action: Callable):
        raise NotImplementedError

    @condition.register
    def _condition(self, determinant: FunctionType, action: Callable):
        """
        Attaches a conditional based determinant to the body of the curried
        function, given one has been assigned. Bounds an action part
        which has to take place, given the decision has not been
        satisfied.
        :determinant:FunctionType
        :action:Callable
        :return:None
        """
        body = self._body
        if not body:
            raise NotImplementedError

        def function(target, *args, **kwargs):
            if determinant(*args, **kwargs):
                return target(*args, **kwargs)
            else:
                return action(*args, **kwargs)

        self.attach(self._wrap(body, function))

    @condition.register
    def _condition(self, determinant: BaseException, action: Callable):
        """
        Attaches an exception based determinant wrapper to the body
        of a curried function, given one has been assigned.
        Bounds an action part which has to take place, given
        the exception has to arise.
        :determinant:Exception
        :action:Callable
        :return:None
        """
        body = self._body
        if not body:
            raise NotImplementedError

        def function(target, *args, **kwargs):
            try:
                output = target(*args, **kwargs)
            except determinant.__class__:
                return action(*args, **kwargs)
            else:
                return output

        self.attach(self._wrap(body, function))

    @property
    def product(self) -> Callable:
        """
        Produces the resulting curried function.
        :returns:Callable
        """
        _ = super(self.__class__, self).product
        body = self._body
        self._reset()
        return body

    def _pre(self, part: Callable):
        """
        Returns a wrapper around previously assigned body function.
        :part:Callable
        :returns:Callable
        """
        body = self._body or (lambda *args, **kwargs: None)
        return self._wrap(body, lambda target, *args, **kwargs: target(
            part(*args, **kwargs)
        ))

    def _post(self, part):
        """
        Returns a wrapper around previously assigned body function.
        :part:Callable
        :returns:Callable
        """
        body = self._body or (lambda *args, **kwargs: None)
        return self._wrap(body, lambda target, *args, **kwargs: part(
            target(*args, **kwargs)
        ))

    @staticmethod
    def _wrap(target: Callable, composition: Callable[[Callable, Tuple, Dict],
                                                      Any]):
        """
        Returns a wrapped Callable target, encapsulating it out a
        callable composition.
        :target:Callable
        :composition:Callable
        :return:Callable
        """
        @wraps(target)
        def wrapper(*args, **kwargs):
            return composition(target, *args, **kwargs)
        return wrapper


class IterativeFunctionBuilder(AbstractBuilder):
    """
    A concrete Builder class, which produces a iterator based
    function, executing attached functions one at a time
    providing independent input.
    """

    def _reset(self):
        self._source = None

    @singledispatchmethod
    def attach(self, part):
        raise NotImplementedError

    @attach.register
    def _attach(self, part: ISource):
        """
        Attaches a concrete source to store functions into.
        :part:ISource
        :returns:None
        """
        self._source = part

    @attach.register
    def _attach(self, part: FunctionType):
        """
        Attaches a function into a source, given one has been assigned,
        otherwise raises an Implementation Error.
        """
        if not self._source:
            raise NotImplementedError('Function attachment could only proceed'
                                      ' after a source has been assigned.')
        self._source.put(part)

    def product(self):
        """
        Produces a function, which iteratively invokes each
        attached function.
        :returns:Callable
        """
        _ = super(self.__class__, self).product
        source = self._source
        iterator = iter(source.get, None)
        self._reset()
        return lambda *args, **kwargs: next(iterator)(*args, **kwargs)
