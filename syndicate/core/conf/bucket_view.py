import re
from os import path, sep
import typing
from abc import ABC, abstractmethod
from typing import Union
from urllib.parse import urlparse

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
    def raw(self, value: str):
        raise NotImplementedError

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
        exception = next(self._validate_raw_data(value), None)
        if exception:
            raise exception
        self._raw = value
        self._parsed = urlparse(value)

    @property
    def name(self) -> Union[str, None]:
        """
        Returns the name of a bucket, retrieving netloc of the url.
        """
        return self._parsed.netloc if self.raw else None

    @property
    def key(self) -> str:
        """
        Returns the key-object path compound.
        """
        return self._parsed.path.lstrip('/') if self.raw else None

    @property
    def ikey(self) -> typing.Iterator:
        """
        Yields each key in the key-object path compound.
        """
        if self.key is not None:
            return iter(path.normpath(self.key).split(sep))
        else:
            raise StopIteration

    @classmethod
    def _validate_raw_data(cls, value):
        exception_mapping = {
            TypeError: dict(
                condition=lambda data: isinstance(data, str),
                message=f'Raw data \'{value}\' must be a string.'
            ),
            cls.InvalidS3URIException: dict(
                condition=lambda data: bool(re.match(r'^s3:\/\/(([0-9a-z\-]+)\/)+$', data)),
                message=f'Raw data must follow the s3 url pattern.'
            )
        }
        return (
            item[0](item[1]['message'])
            for item in exception_mapping.items()
            if not item[1]['condition'](value)
        )

