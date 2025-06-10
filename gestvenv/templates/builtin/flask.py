"""
Template Flask
"""

from typing import Dict, List, Any
from ..base_template import ProjectTemplate, TemplateFile


class FlaskTemplate(ProjectTemplate):
    """Template pour applications Flask"""
    
    def __init__(self):
        super().__init__(
            name="flask",
            description="Application Flask avec blueprints",
            category="web",
            dependencies=[
                "flask>=2.3.0",
                "flask-sqlalchemy>=3.0.0",
                "flask-migrate>=4.0.0",
                "python-dotenv>=1.0.0"
            ],
            dev_dependencies=[
                "pytest>=7.0.0",
                "black>=23.0.0",
                "isort>=5.12.0"
            ]
        )
        
    def get_files(self) -> List[TemplateFile]:
        return [
            TemplateFile(
                path="{{package_name}}/__init__.py",
                content='''"""{{project_name}} - Application Flask"""

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

db = SQLAlchemy()
migrate = Migrate()


def create_app():
    """Factory d'application Flask"""
    app = Flask(__name__)
    
    app.config['SECRET_KEY'] = 'dev-secret-key'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///{{package_name}}.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db.init_app(app)
    migrate.init_app(app, db)
    
    from .views import bp
    app.register_blueprint(bp)
    
    return app
'''
            ),
            TemplateFile(
                path="{{package_name}}/models.py",
                content='''"""Modèles de données"""

from datetime import datetime
from . import db


class Item(db.Model):
    """Modèle d'exemple"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Item {self.name}>'
'''
            ),
            TemplateFile(
                path="{{package_name}}/views.py",
                content='''"""Vues Flask"""

from flask import Blueprint, render_template, jsonify
from .models import Item

bp = Blueprint('main', __name__)


@bp.route('/')
def index():
    """Page d'accueil"""
    return render_template('index.html', title='{{project_name}}')


@bp.route('/api/items')
def api_items():
    """API des items"""
    items = Item.query.all()
    return jsonify([{
        'id': item.id,
        'name': item.name,
        'description': item.description
    } for item in items])
'''
            ),
            TemplateFile(
                path="{{package_name}}/templates/base.html",
                content='''<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% if title %}{{ title }} - {% endif %}{{project_name}}</title>
</head>
<body>
    <nav>
        <h1>{{project_name}}</h1>
    </nav>
    
    <main>
        {% block content %}{% endblock %}
    </main>
</body>
</html>'''
            ),
            TemplateFile(
                path="{{package_name}}/templates/index.html",
                content='''{% extends "base.html" %}

{% block content %}
<h2>Bienvenue dans {{project_name}}</h2>
<p>{{description}}</p>
{% endblock %}'''
            ),
            TemplateFile(
                path="run.py",
                content='''"""Point d'entrée pour développement"""

from {{package_name}} import create_app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True)
'''
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
                    "dev": self.dev_dependencies
                }
            },
            "build-system": {
                "requires": ["setuptools>=61.0", "wheel"],
                "build-backend": "setuptools.build_meta"
            }
        }