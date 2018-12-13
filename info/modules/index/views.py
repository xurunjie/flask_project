from flask import render_template, current_app, session

from info import constants
from info.models import User, News
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
    # get click data ranking
    new_list = None

    try:
        new_list = News.query.order_by(News.clicks.desc()).limit(constants.CLICK_RANK_MAX_NEWS)
    except Exception as e:
        current_app.logger.error(e)

    click_new_list = []
    for new in new_list if new_list else list():
        click_new_list.append(new.to_basic_dict)

    data = {
        'user_info':user.to_dict() if user else None,
        'click_news_list':click_new_list
    }

    return render_template('news/index.html',data=data)


@index_blue.route('/favicon.ico')
def favicon_ico():
    # send static file of favicon.ico
    return current_app.send_static_file('news/favicon.ico')
