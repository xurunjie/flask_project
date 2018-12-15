from flask import render_template, current_app, session, request, jsonify,g

from info import constants
from info.models import User, News, Category
from info.utils.response_code import RET
from info.utils.common import user_login_data
from . import index_blue


@index_blue.route('/')
@user_login_data
def index():
    # get click data ranking
    new_list = None

    try:
        new_list = News.query.order_by(News.clicks.desc()).limit(constants.CLICK_RANK_MAX_NEWS)
    except Exception as e:
        current_app.logger.error(e)

    click_new_list = []
    for new in new_list if new_list else list():
        click_new_list.append(new.to_basic_dict())

    # get categories news types data
    categories = Category.query.all()

    # save category data
    categories_dicts = [category.to_dict() for category in categories]

    data = {
        'user_info': g.user.to_dict() if g.user else None,
        'click_news_list': click_new_list,
        'categories': categories_dicts
    }

    return render_template('news/index.html', data=data)


@index_blue.route('/news_list')
def get_new_list():
    # get params
    data = request.args
    page = data.get('page', 1)
    per_page = data.get('per_page', constants.HOME_PAGE_MAX_NEWS)
    categort_id = data.get('cid', 1)
    # verify params
    try:
        page = int(page)
        categort_id = int(categort_id)
        per_page = int(per_page)
    except Exception as e:
        current_app.logger.info(e)
        return jsonify(error=RET.PARAMERR, error_msg='params must be int not others')

    # filter and pagenation
    filters = []
    if categort_id != 1:
        filters.append(News.category_id == categort_id)

    try:
        paginate = News.query.filter(*filters).order_by(News.create_time.desc()).paginate(page, per_page, False)
    except Exception as e:
        current_app.logger.info(e)
        return jsonify(error=RET.DATAERR, errmsg='data query failed')

    # query success
    items = paginate.items
    total_page = paginate.pages
    current_page = paginate.page

    # serializer
    news_dict_li = [news.to_dict() for news in items]
    data = {
        'news_dict_li': news_dict_li,
        'total_page': total_page,
        'current_page': current_page
    }
    return jsonify(error=RET.OK, errmsg='ok', data=data)


@index_blue.route('/favicon.ico')
def favicon_ico():
    # send static file of favicon.ico
    return current_app.send_static_file('news/favicon.ico')
