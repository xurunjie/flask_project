from flask import Blueprint

index_blue = Blueprint('/',__name__)

from . import views