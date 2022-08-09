from . import AbstractResponsibilityNode
from typing import Union, Callable
from inspect import signature


class BlackBoxResponsibilityNode(AbstractResponsibilityNode):
    """
    A concrete responsibility node class, which delegates execution
    to an outsourced computation treated as the Oracle Black Box.
    """

    def __init__(self):
        super().__init__()
        self._box = None

    @property
    def box(self) -> Union[Callable, None]:
        """
        Returns the outsourced black box oracle.
        :returns:Union[None,Callable]
        """
        return self._box

    @box.setter
    def box(self, other: Callable):
        """
        Sets an oracle based black-box computation in a form of callable
        function.
        :other:Callable
        :returns:None
        """
        if not isinstance(other, Callable):
            raise TypeError('An outsourced computable must be '
                            'of a callable type.')
        if len(signature(other).parameters) !=\
                len(signature(self.handle).parameters):
            raise RuntimeError(f'A callable must contain the same '
                               f'amount of parameters as `handle` method.')
        self._box = other

    def handle(self, data):
        """
        Passes along the `output`, which could be denoted either as:
            - an output of an outsourced callable black-box oracle;
            - the incoming payload, given the aforementioned state
            had been satisfied.
        At last returns the chained co-output.
        returns:Any
        """
        return super(self.__class__, self).handle(
            self.box(data) if self.box else data
        )
