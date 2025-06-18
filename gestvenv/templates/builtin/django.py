"""
Template Django
"""

from typing import Dict, List, Any
from ..base_template import ProjectTemplate, TemplateFile


class DjangoTemplate(ProjectTemplate):
    """Template pour projets Django"""
    
    def __init__(self):
        super().__init__(
            name="django",
            description="Projet Django avec configuration moderne",
            category="web",
            dependencies=[
                "django>=4.2.0",
                "django-environ>=0.10.0",
                "psycopg2-binary>=2.9.0"
            ],
            dev_dependencies=[
                "pytest>=7.0.0",
                "pytest-django>=4.5.0",
                "black>=23.0.0",
                "isort>=5.12.0",
                "django-debug-toolbar>=4.0.0"
            ]
        )
        
    def get_files(self) -> List[TemplateFile]:
        return [
            TemplateFile(
                path="{{package_name}}/settings.py",
                content='''"""Configuration Django pour {{project_name}}"""

from pathlib import Path
import environ

env = environ.Env(
    DEBUG=(bool, False)
)

BASE_DIR = Path(__file__).resolve().parent.parent

environ.Env.read_env(BASE_DIR / '.env')

DEBUG = env('DEBUG')
SECRET_KEY = env('SECRET_KEY', default='django-insecure-dev-key')

ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['localhost', '127.0.0.1'])

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'core',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = '{{package_name}}.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Europe/Paris'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
'''
            ),
            TemplateFile(
                path="{{package_name}}/urls.py",
                content='''"""URLs principales de {{project_name}}"""

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
]
'''
            ),
            TemplateFile(
                path="core/__init__.py",
                content="",
                is_template=False
            ),
            TemplateFile(
                path="core/models.py",
                content='''"""Modèles de l'application core"""

from django.db import models


class Item(models.Model):
    """Modèle d'exemple"""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Item"
        verbose_name_plural = "Items"
        ordering = ['-created_at']
'''
            ),
            TemplateFile(
                path="core/views.py",
                content='''"""Vues de l'application core"""

from django.shortcuts import render
from django.http import JsonResponse
from .models import Item


def index(request):
    """Vue d'accueil"""
    return render(request, 'core/index.html', {
        'title': '{{project_name}}'
    })


def api_items(request):
    """API des items"""
    items = Item.objects.all()
    data = [
        {
            'id': item.id,
            'name': item.name,
            'description': item.description
        }
        for item in items
    ]
    return JsonResponse({'items': data})
'''
            ),
            TemplateFile(
                path="core/urls.py",
                content='''"""URLs de l'application core"""

from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('api/items/', views.api_items, name='api_items'),
]
'''
            ),
            TemplateFile(
                path="manage.py",
                content='''#!/usr/bin/env python
"""Utilitaire de gestion Django pour {{project_name}}"""

import os
import sys

if __name__ == '__main__':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', '{{package_name}}.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed?"
        ) from exc
    execute_from_command_line(sys.argv)
'''
            ),
            TemplateFile(
                path=".env.example",
                content='''# Configuration pour {{project_name}}
DEBUG=True
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=localhost,127.0.0.1
''',
                is_template=False
            )
        ]
        
    def get_pyproject_config(self) -> Dict[str, Any]:
        return {
            "project": {
                "name": "{{project_name}}",
                "version": "{{version}}",
                "description": "{{description}}",
                "authors": [{"name": "{{author}}", "email": "{{email}}"}],
                "license": {"text": "{{license}}"},
                "readme": "README.md",
                "requires-python": ">=3.8",
                "dependencies": self.dependencies,
                "optional-dependencies": {
                    "dev": self.dev_dependencies,
                    "prod": ["gunicorn>=20.0.0", "whitenoise>=6.0.0"]
                }
            },
            "build-system": {
                "requires": ["setuptools>=61.0", "wheel"],
                "build-backend": "setuptools.build_meta"
            }
        }