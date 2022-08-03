from . import IBuilder
from abc import abstractmethod


class AbstractBuilder(IBuilder):
    def __init__(self):
        self._reset()

    @property
    @abstractmethod
    def product(self):
        """
        Verifies that each instance attribute has been assigned, otherwise
        raises the NotImplementedError exception.
        :raises: NotImplementedError
        """
        unassigned = next(
            filter(lambda item: not bool(item[1]), self.__dict__.items()), None
        )
        if unassigned is not None:
            raise NotImplementedError(f'Production has been halted, due to an'
                                      f' attribute `{unassigned[0]}` not being '
                                      f'assigned.')



