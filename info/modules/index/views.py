from flask import render_template, current_app
from . import index_blue


@index_blue.route('/')
def index():
    return render_template('news/index.html')


@index_blue.route('/favicon.ico')
def favicon_ico():
    # send static file of favicon.ico
    return current_app.send_static_file('news/favicon.ico')
