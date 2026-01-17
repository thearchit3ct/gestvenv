"""
Templates intégrés pour GestVenv v1.1
"""

from .basic import BasicTemplate
from .web import WebTemplate
from .data_science import DataScienceTemplate
from .cli import CLITemplate
from .fastapi import FastAPITemplate
from .flask import FlaskTemplate
from .django import DjangoTemplate

__all__ = [
    'BasicTemplate',
    'WebTemplate', 
    'DataScienceTemplate',
    'CLITemplate',
    'FastAPITemplate',
    'FlaskTemplate',
    'DjangoTemplate'
]