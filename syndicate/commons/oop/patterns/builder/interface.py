from abc import ABC, abstractmethod


class IBuilder(ABC):

    @abstractmethod
    def _reset(self):
        ...

    @property
    @abstractmethod
    def product(self):
        ...

    @abstractmethod
    def attach(self, part):
        ...