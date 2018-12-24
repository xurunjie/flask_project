import time
from datetime import datetime, timedelta

from flask import current_app, jsonify
from flask import g
from flask import redirect
from flask import render_template
from flask import request
from flask import session
from flask import url_for

from info import constants, db
from info.models import News, Category, User
from info.utils.common import user_login_data
from info.utils.response_code import RET
from info.utils.image_storage import storage
from . import admin_blue


@admin_blue.route('/')
def redirect_page():
    return redirect(url_for('admin.admin_login'))

@admin_blue.route('/login', methods=["POST", "GET"])
def admin_login():
    if request.method == "GET":

        user_id = session.get("user_id", None)
        is_admin = session.get("is_admin", False)

        if user_id and is_admin:
            return redirect(url_for('admin.admin_index'))
        return render_template('admin/login.html')


    username = request.form.get("username")
    password = request.form.get("password")

    if not all([username, password]):
        return render_template('admin/login.html', errmsg="参数错误")

    try:
        user = User.query.filter(User.mobile == username).first()
    except Exception as e:
        current_app.logger.error(e)
        return render_template('admin/login.html', errmsg="数据查询错误")

    if not user or not user.check_passowrd(password):
        return render_template('admin/login.html', errmsg="账号或密码不对")

    if not user.is_admin:
        return render_template('admin/login.html', errmsg="用户权限不足")

    session["user_id"] = user.id
    session["nick_name"] = user.nick_name
    session['moblie'] = user.mobile
    session['is_admin'] = True

    return redirect(url_for('admin.admin_index'))


@admin_blue.route('/index')
@user_login_data
def admin_index():
    user = g.user
    return render_template('admin/index.html', user=user.to_dict())


@admin_blue.route('/user_count')
def user_count():
    total_count = 0
    try:
        total_count = User.query.filter(User.is_admin == False).count()
    except Exception as e:
        current_app.logger.error(e)


    mon_count = 0
    try:
        now = time.localtime()
        mon_begin = '%d-%02d-01' % (now.tm_year, now.tm_mon)
        mon_begin_date = datetime.strptime(mon_begin, '%Y-%m-%d')
        mon_count = User.query.filter(User.is_admin == False, User.create_time >= mon_begin_date).count()
    except Exception as e:
        current_app.logger.error(e)

    day_count = 0
    try:
        day_begin = '%d-%02d-%02d' % (now.tm_year, now.tm_mon, now.tm_mday)
        day_begin_date = datetime.strptime(day_begin, '%Y-%m-%d')
        day_count = User.query.filter(User.is_admin == False, User.create_time > day_begin_date).count()
    except Exception as e:
        current_app.logger.error(e)

    # query table infomations

    now_date = datetime.strptime(datetime.now().strftime('%Y-%m-%d'), '%Y-%m-%d')
    active_date = []
    active_count = []

    for i in range(0, 31):
        begin_date = now_date - timedelta(days=i)
        end_date = now_date - timedelta(days=(i - 1))
        active_date.append(begin_date.strftime('%Y-%m-%d'))
        count = 0
        try:
            count = User.query.filter(User.is_admin == False, User.last_login >= day_begin,
                                      User.last_login < end_date).count()
        except Exception as e:
            current_app.logger.error(e)
        active_count.append(count)

    active_date.reverse()
    active_count.reverse()

    data = {"total_count": total_count, "mon_count": mon_count, "day_count": day_count, "active_date": active_date,
            "active_count": active_count}

    return render_template('admin/user_count.html', data=data)


@admin_blue.route('/user_list')
def user_list():

    page = request.args.get("page", 1)
    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        page = 1

    users = []
    current_page = 1
    total_page = 1


    try:
        paginate = User.query.filter(User.is_admin == False).order_by(User.last_login.desc()).paginate(page,
                                                                                                       constants.ADMIN_USER_PAGE_MAX_COUNT,
                                                                                                       False)
        users = paginate.items
        current_page = paginate.page
        total_page = paginate.pages
    except Exception as e:
        current_app.logger.error(e)

    users_list = []
    for user in users:
        users_list.append(user.to_admin_dict())

    context = {
        "total_page": total_page,
        "current_page": current_page,
        "users": users_list
    }
    return render_template('admin/user_list.html', data=context)


@admin_blue.route('/news_review')
def news_review():

    page = request.args.get("p", 1)
    keywords = request.args.get("keywords", "")
    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        page = 1

    news_list = []
    current_page = 1
    total_page = 1

    try:
        filters = [News.status != 0]
        if keywords:
            filters.append(News.title.contains(keywords))
        paginate = News.query.filter(*filters) \
            .order_by(News.create_time.desc()) \
            .paginate(page, constants.ADMIN_NEWS_PAGE_MAX_COUNT, False)

        news_list = paginate.items
        current_page = paginate.page
        total_page = paginate.pages
    except Exception as e:
        current_app.logger.error(e)

    news_dict_list = []
    for news in news_list:
        news_dict_list.append(news.to_review_dict())

    context = {
        "total_page": total_page,
        "current_page": current_page,
        "news_list": news_dict_list
    }

    return render_template('admin/news_review.html', data=context)


@admin_blue.route('/news_review_detail', methods=["POST", "GET"])
def news_review_detail():

    if request.method == "GET":

        news_id = request.args.get("news_id")
        if not news_id:
            return render_template('admin/news_review_detail.html', data={"errmsg": "未查询到此新闻"})

        news = None
        try:
            news = News.query.get(news_id)
        except Exception as e:
            current_app.logger.error(e)

        if not news:
            return render_template('admin/news_review_detail.html', data={"errmsg": "未查询到此新闻"})


        data = {"news": news.to_dict()}
        return render_template('admin/news_review_detail.html', data=data)

    news_id = request.json.get("news_id")
    action = request.json.get("action")


    if not all([news_id, action]):
        return jsonify(error=RET.PARAMERR, errmsg="参数错误")
    if action not in ("accept", "reject"):
        return jsonify(error=RET.PARAMERR, errmsg="参数错误")

    news = None
    try:
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)

    if not news:
        return jsonify(error=RET.NODATA, errmsg="未查询到数据")

    if action == "accept":
        news.status = 0
    else:
        reason = request.json.get("reason")
        if not reason:
            return jsonify(error=RET.PARAMERR, errmsg="参数错误")
        news.reason = reason
        news.status = -1

    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(error=RET.DBERR, errmsg="数据保存失败")
    return jsonify(error=RET.OK, errmsg="操作成功")


@admin_blue.route('/news_edit')
def news_edit():
    page = request.args.get("p", 1)
    keywords = request.args.get("keywords", "")
    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        page = 1

    news_list = []
    current_page = 1
    total_page = 1

    try:
        filters = []
        if keywords:
            filters.append(News.title.contains(keywords))

        paginate = News.query.filter(*filters) \
            .order_by(News.create_time.desc()) \
            .paginate(page, constants.ADMIN_NEWS_PAGE_MAX_COUNT, False)

        news_list = paginate.items
        current_page = paginate.page
        total_page = paginate.pages
    except Exception as e:
        current_app.logger.error(e)

    news_dict_list = []
    for news in news_list:
        news_dict_list.append(news.to_basic_dict())

    context = {"total_page": total_page, "current_page": current_page, "news_list": news_dict_list}

    return render_template('admin/news_edit.html', data=context)


@admin_blue.route('/news_edit_detail', methods=["GET", "POST"])
def news_edit_detail():
    if request.method == "GET":
        news_id = request.args.get("news_id")

        if not news_id:
            return render_template('admin/news_edit_detail.html', data={"errmsg": "未查询到此新闻"})

        news = None
        try:
            news = News.query.get(news_id)
        except Exception as e:
            current_app.logger.error(e)

        if not news:
            return render_template('admin/news_edit_detail.html', data={"errmsg": "未查询到此新闻"})

        categories = Category.query.all()
        categories_li = []
        for category in categories:
            c_dict = category.to_dict()
            c_dict["is_selected"] = False
            if category.id == news.category_id:
                c_dict["is_selected"] = True
            categories_li.append(c_dict)
        categories_li.pop(0)

        data = {"news": news.to_dict(), "categories": categories_li}
        return render_template('admin/news_edit_detail.html', data=data)

    news_id = request.form.get("news_id")
    title = request.form.get("title")
    digest = request.form.get("digest")
    content = request.form.get("content")
    index_image = request.files.get("index_image")
    category_id = request.form.get("category_id")
    if not all([title, digest, content, category_id]):
        return jsonify(error=RET.PARAMERR, errmsg="参数有误")

    news = None
    try:
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)
    if not news:
        return jsonify(error=RET.NODATA, errmsg="未查询到新闻数据")

    if index_image:
        try:
            index_image = index_image.read()
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(error=RET.PARAMERR, errmsg="参数有误")

        try:
            key = storage(index_image)
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(error=RET.THIRDERR, errmsg="上传图片错误")
        news.index_image_url = constants.QINIU_DOMIN_PREFIX + key
    news.title = title
    news.digest = digest
    news.content = content
    news.category_id = category_id

    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(error=RET.DBERR, errmsg="保存数据失败")
    return jsonify(error=RET.OK, errmsg="编辑成功")


@admin_blue.route('/news_category')
def get_news_category():
    categories = Category.query.all()
    categories_dicts = []

    for category in categories:
        cate_dict = category.to_dict()
        categories_dicts.append(cate_dict)

    categories_dicts.pop(0)
    return render_template('admin/news_type.html', data={"categories": categories_dicts})


@admin_blue.route('/add_category', methods=["POST"])
def add_category():

    category_id = request.json.get("id")
    category_name = request.json.get("name")
    if not category_name:
        return jsonify(error=RET.PARAMERR, errmsg="参数错误")
    if category_id:
        try:
            category = Category.query.get(category_id)
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(error=RET.DBERR, errmsg="查询数据失败")

        if not category:
            return jsonify(error=RET.NODATA, errmsg="未查询到分类信息")

        category.name = category_name
    else:
        category = Category()
        category.name = category_name
        db.session.add(category)

    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(error=RET.DBERR, errmsg="保存数据失败")
    return jsonify(error=RET.OK, errmsg="保存数据成功")


@admin_blue.route('/logout')
@user_login_data
def logout():
    session.pop('user_id', None)
    session.pop('nick_name', None)
    session.pop('mobile', None)
    session.pop('is_admin', None)
    return redirect(url_for('admin.admin_login'))
