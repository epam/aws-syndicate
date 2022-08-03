from abc import ABC, abstractmethod


class IRelation(ABC):

    @property
    @abstractmethod
    def reference(self):
        ...

    @reference.setter
    @abstractmethod
    def reference(self, other):
        ...


class IReference(ABC):
    @property
    @abstractmethod
    def commitment(self):
        ...

    @commitment.setter
    @abstractmethod
    def commitment(self, other):
        ...

