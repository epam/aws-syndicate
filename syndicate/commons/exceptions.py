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


class SDCTBaseError(Exception):
    """
    The base exception class for syndicate exceptions.
    """
    pass


# =============================================================================
class SDCTNotImplementedError(SDCTBaseError):
    """
    The syndicate not implemented error.
    """
    pass


class InternalError(SDCTBaseError):
    """
    The syndicate internal error.
    """
    pass


class AbortedError(SDCTBaseError):
    """
    The operation abortion error.
    """
    pass


class InvalidValueError(SDCTBaseError):
    """
    The value error.
    """
    pass


class InvalidTypeError(SDCTBaseError):
    """
    The type error.
    """
    pass


# =============================================================================
class ProjectStateError(SDCTBaseError):
    """
    Project state error.
    """
    pass


# =============================================================================
class SDCTConfigurationError(SDCTBaseError):
    """
    The syndicate configuration error.
    """
    pass


# =============================================================================
class SDCTEnvironmentError(SDCTBaseError):
    """
    The syndicate environment error.
    """
    pass


# =============================================================================
class ResourceProcessingError(SDCTBaseError):
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


class ParameterValueError(ResourceMetadataError):
    """
    The value of the parameter is invalid.
    """
    pass


# =============================================================================
