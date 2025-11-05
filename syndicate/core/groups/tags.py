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
import click

from syndicate.commons.log_helper import get_user_logger
from syndicate.core.constants import OK_RETURN_CODE, FAILED_RETURN_CODE
from syndicate.core.decorators import return_code_manager, tags_to_context
from syndicate.core.helper import verbose_option

TAGS_GROUP_NAME = 'tags'


USER_LOG = get_user_logger()


@click.group(name=TAGS_GROUP_NAME)
@return_code_manager
def tags():
    """Manage resources tags"""


@tags.command(name='apply')
@return_code_manager
@tags_to_context
@verbose_option
@click.pass_context
def apply(ctx):
    """Assign tags from config to deployed resources"""
    output = ctx.obj['output']
    success = ctx.obj['tags_resource'].safe_apply_tags(output)
    if success:
        USER_LOG.info("Tags applied successfully")
        return OK_RETURN_CODE
    else:
        USER_LOG.warning(
            "Tags applied with errors. More details in the log file"
        )
        return FAILED_RETURN_CODE


@tags.command(name='remove')
@return_code_manager
@tags_to_context
@verbose_option
@click.pass_context
def remove(ctx):
    """Remove tags from config from deployed resources"""
    output = ctx.obj['output']
    success = ctx.obj['tags_resource'].safe_remove_tags(output)
    if success:
        USER_LOG.info("Tags removed successfully")
        return OK_RETURN_CODE
    else:
        USER_LOG.warning(
            "Tags removed with errors. More details in the log file"
        )
        return FAILED_RETURN_CODE
