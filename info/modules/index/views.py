from flask import render_template, current_app, session

from info.models import User
from . import index_blue


@index_blue.route('/')
def index():
    # get user id from session
    user_id = session.get('user_id')
    # select user info
    user = None
    if user_id:
        try:
            user = User.query.get(user_id)
        except Exception as e:
            current_app.logger.error(e)
    # serializer user info
    data = {
        'user_info':user.to_dict() if user else None
    }

    return render_template('news/index.html',data=data)


@index_blue.route('/favicon.ico')
def favicon_ico():
    # send static file of favicon.ico
    return current_app.send_static_file('news/favicon.ico')
