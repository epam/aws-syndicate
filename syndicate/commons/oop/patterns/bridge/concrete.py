from . import (IRelation, IReference, AbstractSource, IStore)

from queue import Queue

from typing import Union, Type

class OneToOneRelation(IRelation):

    def __init__(self):
        self._reference = None

    @property
    def reference(self) -> Union[IReference, Type[None]]:
        """
        Returns a related reference object.
        :returns:Union[None, IReference]
        """
        return self._reference

    @reference.setter
    def reference(self, other: IReference):
        """
        Sets up a related reference object.
        :other:IReference
        :returns:None
        """
        if not isinstance(other, IReference):
            raise TypeError('A reference must be of IReference class.')
        self._reference = other


class InterchangeableReference(IReference):
    """
    A concrete Reference class, which provides behaviour to retain
    the initial commitment, treating incoming ones as ephemeral.
    """

    def __init__(self):
        self._commitment = None

    @property
    def commitment(self):
        """
        Returns a currently persisted commitment.
        :returns:Any
        """
        return self._commitment

    @commitment.setter
    def commitment(self, other):
        """
        Sets a commitment to persist for the current point at time.
        :other:Any
        :returns:None
        """
        self._commitment = other

    @commitment.deleter
    def commitment(self):
        self._commitment = None


class RetainedReference(InterchangeableReference):
    """
    A concrete Reference class, which provides behaviour to retain
    the initial commitment, treating incoming ones as ephemeral.
    """

    def __init__(self):
        super(self.__class__, self).__init__()
        self._transient = Queue()

    @property
    def commitment(self):
        """
        Returns a commitment being compelled to preference the ephemeral
        ones.
        :returns:Any
        """
        return self._transient.get() if not self._transient.empty() \
            else self._commitment

    @commitment.setter
    def commitment(self, other):
        """
        Sets a transient commitment or one to be retained,
        given the incoming one is the initial one.
        :other:Any
        :returns:None
        """
        if not self._commitment:
            self._commitment = other
        else:
            self._transient.put(other)

    @commitment.deleter
    def commitment(self):
        self._commitment = None
        self._transient = Queue()


class PriorityBasedSource(AbstractSource):
    """
    Concrete simple source class, which provides behaviour
    for data priority-based retrieval and insertion, discarding the state
    of IStore association, defaulting to None.
    """
    def get(self):
        """
        Returns data out of the store, defaulting to None, given the
        store has not been assigned.
        :return:Union[Any, None]
        """
        return self.store.get() if self.store else None

    def put(self, data):
        """
        Puts data into a store, given one has been assigned.
        """
        if self.store:
            self.store.put(data)


class QueueStore(IStore):
    """
    A concrete Store class, providing FIFO based behaviour of
    data retrieval and insertion.
    """

    def __init__(self):
        self._queue = Queue()

    def get(self):
        """
        Returns data out of the queue, adhering to the FIFO approach,
        providing None as a default.
        :return:Union[Any, None]
        """
        return self._queue.get() if not self._queue.empty() else None

    def put(self, data):
        """
        Inserts data into the queue, adhering to the FIFO approach.
        :return:None
        """
        self._queue.put(data)
