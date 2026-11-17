from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow

# Initialize SQLAlchemy ORM
db = SQLAlchemy()

# Initialize Marshmallow serialization framework
ma = Marshmallow()
