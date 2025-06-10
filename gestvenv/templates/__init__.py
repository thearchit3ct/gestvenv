"""
Module templates pour GestVenv v1.1
"""

from .base_template import ProjectTemplate, TemplateFile, TemplateMetadata
from .builtin import (
    BasicTemplate,
    WebTemplate, 
    DataScienceTemplate,
    CLITemplate,
    FastAPITemplate,
    FlaskTemplate,
    DjangoTemplate
)

__all__ = [
    'ProjectTemplate',
    'TemplateFile', 
    'TemplateMetadata',
    'BasicTemplate',
    'WebTemplate',
    'DataScienceTemplate', 
    'CLITemplate',
    'FastAPITemplate',
    'FlaskTemplate',
    'DjangoTemplate'
]