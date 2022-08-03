from abc import ABC, abstractmethod

class IResponsibilityNode(ABC):

    @property
    @abstractmethod
    def relation(self):
        """
        Meant to return a directed connection-wise wiring, between nodes.
        """

    @relation.setter
    @abstractmethod
    def relation(self, other):
        """
        Meant to set a directed connection-wise wiring, between nodes.
        """

    @abstractmethod
    def handle(self, data):
        """
        Meant to handle any incoming data.
        """
        ...
