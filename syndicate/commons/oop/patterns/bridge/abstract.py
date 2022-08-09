from . import ISource, IStore

class AbstractSource(ISource):

    def __init__(self):
        self._store = None

    @property
    def store(self):
        """
        Returns an assigned store:IStore instance or None.
        :returns:Union[None, IStore]
        """
        return self._store

    @store.setter
    def store(self, other: IStore):
        """
        Sets up a related store object.
        :other:IStore
        :returns:None
        """
        if not isinstance(other, IStore):
            raise TypeError('A store must be of IStore class.')
        self._reference = other
