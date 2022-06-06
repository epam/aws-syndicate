import re
from abc import ABC, abstractmethod
from typing import Union
from collections.abc import Iterable

NAMED_S3_URI_PATTERN = r'^(?P<proto>s3:\/\/)?(?:(?P<name>[0-9a-z\-]+)' \
                       r'(?:\/)?)(?P<key>(?<=\/)(?:[0-9a-z\-_]+(?:\/)?)+)?$'
S3_PATTERN_GROUP_NAMES = ('proto', 'name', 'key')


class AbstractViewDigest(ABC):
    """
    Abstract parsing view class.
    """
    @abstractmethod
    def parse(self, value: str):
        if not isinstance(value, str):
            raise TypeError('Value to be parsed must be of string type.')


class RegexViewDigest(AbstractViewDigest):
    def __init__(self):
        self._expression = None
        self._groups: Iterable = tuple()

    def parse(self, value: str) -> dict:
        """
        Regex digestion of the incoming string value.
        :return: dict | keys = self.groups
        """
        super(self.__class__, self).parse(value)
        if not self.expression:
            raise RuntimeError('No expression has been assigned.')
        match = self.expression.match(value)
        return match.groupdict() if match else dict()

    @property
    def expression(self):
        return self._expression

    @expression.setter
    def expression(self, pattern: str):
        """
        Prepares a regex expression, based on the provided pattern.
        The pattern is assigned, only if the expression contains
        requires groups, if there are any.
        """
        try:
            pending = re.compile(pattern)
        except re.error as exception:
            raise exception

        if any(each for each in self.groups if each not in pending.groupindex):
            raise KeyError(f'Pattern {pattern}, must include'
                           f' named groups {", ".join(self.groups)}')
        self._expression = pending

    @property
    def groups(self) -> Iterable:
        return self._groups

    @groups.setter
    def groups(self, other: Iterable):
        """
        Sets up required expression groups
        as an iterable collection of strings.
        """
        if not isinstance(other, Iterable) and any(
            each for each in other if not isinstance(each,str)
        ):
            raise TypeError('Required groups must be an iterable'
                            ' and contain only string elements.')
        self._groups = other


class AbstractBucketView(ABC):
    """
    Abstract bucket view.
    """
    class BucketViewRuntimeError(RuntimeError):
        """
        The runtime parent bucket view error class.
        """

    def __init__(self):
        self._raw = None
        self._digest = None

    @property
    @abstractmethod
    def name(self):
        raise NotImplementedError

    @property
    @abstractmethod
    def raw(self):
        return self._raw

    @raw.setter
    @abstractmethod
    def raw(self, value: str) -> None:
        """
        Abstract raw value setter, which provides
        argument type verification.
        :raises: TypeError
        """
        if not self.digest:
            raise self.BucketViewRuntimeError('View digest hasn\'t been set.')
        if not isinstance(value, str):
            raise TypeError('Raw value must be of string type.')

    @property
    def digest(self):
        return self._digest

    @digest.setter
    def digest(self, other: AbstractViewDigest):
        if isinstance(other, AbstractViewDigest):
            self._digest = other
        else:
            raise TypeError('View digest-parser must '
                            'be of AbstractViewDigest type.')


class URIBucketView(AbstractBucketView):

    class InvalidS3URIException(AbstractBucketView.BucketViewRuntimeError):
        """
        An error class, meant to thrown once an invalid S3 URI is inputted.
        """

    def __init__(self):
        """
        Initializes a bucket view, with an empty parsed-value maintainer.
        """
        super(self.__class__, self).__init__()
        self._parsed = None

    @property
    def raw(self) -> Union[str, None]:
        return self._raw

    @raw.setter
    def raw(self, value: str):
        """
        Installs a raw url value, which alters the
        parsed-value maintainer in runtime.
        """
        super(self.__class__, self.__class__).raw.fset(self, value)
        self._raw = value
        self._parsed = self.digest.parse(value)

    @property
    def name(self) -> Union[str, None]:
        """
        Returns the name of a bucket, retrieving netloc of the url.
        """
        value = self._parsed.get('name', '') if self._parsed else None
        return '' if value is None else value

    @property
    def key(self) -> str:
        """
        Returns the key-object path compound.
        """
        value = self._parsed.get('key', '') if self._parsed else None
        return '' if value is None else value

