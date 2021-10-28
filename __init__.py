import datetime
from flask import Flask

def create_app(config_name):
    app = Flask(__name__)
    #app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:postgres@127.0.0.1:5432/postgres'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///conversor.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JWT_SECRET_KEY']='frase-secreta'
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = 3600
    app.config['PROPAGATE_EXCEPTIONS'] = True
    return app