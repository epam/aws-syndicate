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

class ISource(ABC):

    @abstractmethod
    def get(self):
        ...

    @abstractmethod
    def put(self, data):
        ...

    @property
    @abstractmethod
    def store(self):
        ...

    @store.setter
    @abstractmethod
    def store(self, other):
        ...

class IStore(ABC):
    @abstractmethod
    def get(self):
        ...

    @abstractmethod
    def put(self, data):
        ...

