from flask import jsonify, session, current_app, render_template, g, abort

from info import constants
from info.models import User, News
from . import news_blue
from info.utils.common import user_login_data


@news_blue.route('/<int:news_id>')
@user_login_data
def news_detail(news_id):
    # click new list
    new_list = None

    try:
        new_list = News.query.order_by(News.clicks.desc()).limit(constants.CLICK_RANK_MAX_NEWS)
    except Exception as e:
        current_app.logger.error(e)

    click_new_list = []
    for new in new_list if new_list else list():
        click_new_list.append(new.to_basic_dict())

    news = None

    try:
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.info(e)
        # not find page
        abort(404)

    if news:
        news.clicks += 1

    data = {
        'user_info': g.user.to_dict() if g.user else None,
        'click_new_list': click_new_list,
        'news':news.to_dict()
    }
    return render_template('news/detail.html', data=data)
