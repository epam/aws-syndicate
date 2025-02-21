"""
    Copyright 2018 EPAM Systems, Inc.

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
"""


class SyndicateBaseError(Exception):
    """
    The base exception class for syndicate exceptions.
    """
    pass


# =============================================================================
class NotImplementedError(SyndicateBaseError):
    """
    The syndicate not implemented error.
    """
    pass


class InternalError(SyndicateBaseError):
    """
    The syndicate internal error.
    """
    pass


class AbortedError(SyndicateBaseError):
    """
    The operation abortion error.
    """
    pass


class InvalidValueError(SyndicateBaseError):
    """
    The value error.
    """
    pass


class InvalidTypeError(SyndicateBaseError):
    """
    The type error.
    """
    pass


# =============================================================================
class ProjectStateError(SyndicateBaseError):
    """
    Project state error.
    """
    pass


# =============================================================================
class ConfigurationError(SyndicateBaseError):
    """
    The syndicate configuration error.
    """
    pass


# =============================================================================
class EnvironmentError(SyndicateBaseError):
    """
    The syndicate environment error.
    """
    pass


# =============================================================================
class ResourceProcessingError(SyndicateBaseError):
    """
    The resource processing error.
    """
    pass


class ArtifactError(ResourceProcessingError):
    """
    The artifact error.
    """
    pass


class ArtifactAssemblingError(ResourceProcessingError):
    """
    The artifact error.
    """
    pass


class ResourceNotFoundError(ResourceProcessingError):
    """
    The resource cannot be found.
    """
    pass


# -----------------------------------------------------------------------------
class ResourceMetadataError(ResourceProcessingError):
    """
    The resource metadata error.
    """
    pass


class ParameterError(ResourceMetadataError):
    """
    The resource metadata parameter error.
    """
    pass


# =============================================================================
