from . import IResponsibilityNode
from .. import IRelation

from abc import abstractmethod


class AbstractResponsibilityNode(IResponsibilityNode):
    def __init__(self):
        self._relation = None

    @property
    def relation(self):
        """
        Returns a designated, association wise, relation complement.
        :returns:Union[None,IWiring]
        """
        return self._relation

    @relation.setter
    def relation(self, other: IRelation):
        """
        Sets an association wise, relation complement.
        :other:IRelation
        :returns:None
        """
        if not isinstance(other, IRelation):
            raise TypeError('A wiring complement must be of IWiring type.')
        self._relation = other

    @abstractmethod
    def handle(self, data):
        """
        Takes on the responsibility of perpetuating the incoming data
        to the bounded reference of the attached relation, given that
        such commitment is of IResponsibilityNode type.
        :data:Any
        :returns:Any
        """
        reference = self.relation.reference if self.relation else None
        commitment = reference.commitment if reference else None
        condition = isinstance(commitment, IResponsibilityNode)
        return commitment.handle(data) if condition else data
