from flask import g, request, render_template, redirect, jsonify, current_app, session, abort

from info import db, constants
from info.models import Category, News, User
from info.utils.image_storage import storage
from info.utils.response_code import RET
from . import profile_blue
from info.utils.common import user_login_data


@profile_blue.route('/info')
@user_login_data
def profile_info():
    user = g.user
    if not user:
        return redirect('/')

    data = {
        'user_info': user.to_dict()
    }
    return render_template('news/user.html', data=data)


@profile_blue.route('/base_info', methods=["POST", 'GET'])
@user_login_data
def base_info():
    """
    get user infomations
    """
    user = g.user
    if request.method == 'GET':
        data = {
            'user_info': user.to_dict()
        }
        return render_template('news/user_base_info.html', data=data)

    # get params
    data = request.json
    nick_name = data.get('nick_name')
    gender = data.get('gender')
    signature = data.get('signature')

    # verify params
    if not all([nick_name, gender, signature]):
        return jsonify(error=RET.PARAMERR, errmsg='parmas is not full')

    if gender not in (['MAN', 'WOMEN']):
        return jsonify(error=RET.PARAMERR, errmsg='params is error')

    # update and save data
    user.nick_name = nick_name
    user.gender = gender
    user.signature = signature

    # commit
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(error=RET.DBERR, errmsg='save data failed')

    session['nick_name'] = nick_name
    return jsonify(error=RET.OK, errmsg='is updating')


@profile_blue.route('/pic_info', methods=['POST', 'GET'])
@user_login_data
def pic_info():
    user = g.user
    if request.method == 'GET':
        data = {
            'user_info': user.to_dict()
        }
        return render_template('news/user_pic_info.html', data=data)

    try:
        # params
        avatar_file = request.files.get('avatar').read()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(error=RET.PARAMERR, errmsg='file read failed')

    # upload file to qiniu stack
    try:
        url = storage(avatar_file)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(error=RET.THIRDERR, errmsg='upload image error')

    # syschronize image to web client
    user.avatar_url = url
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(error=RET.DBERR, errmsg='save user data error')
    data = {
        'avatar_url': constants.QINIU_DOMIN_PREFIX + url
    }

    return jsonify(error=RET.OK, errmsg='ok', data=data)


@profile_blue.route('/pass_info', methods=['GET', 'POST'])
@user_login_data
def pass_info():
    if request.method == 'GET':
        return render_template('news/user_pass_info.html')

    # params
    data = request.json
    old_password = data.get('old_password')
    new_password = data.get('new_password')

    if not all([old_password, new_password]):
        return jsonify(error=RET.OK, errmsg='parmas is not full')

    user = g.user
    # verify init password
    if not user.check_passowrd(old_password):
        return jsonify(error=RET.PWDERR, errmsg='old password is not true')
    if old_password == new_password:
        return jsonify(error=RET.PWDERR, errmsg='old password and new password can not be the same')
    user.password = new_password
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(error=RET.OK, errmsg='save password failed')

    return jsonify(error=RET.OK, errmsg='save data success')


@profile_blue.route('/collection', methods=['GET', 'POST'])
@user_login_data
def user_collection():
    # get page from args
    page = request.args.get('page')
    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        page = 1
    user = g.user
    collections = list()
    # query collect news
    try:
        paginate = user.collection_news.paginate(page, constants.USER_COLLECTION_MAX_NEWS, False)
        # get data
        collections = paginate.items
        # get current page
        current_page = paginate.page
        # get total page
        total_page = paginate.pages

    except Exception as e:
        current_app.logger.error(e)

    collection_dict_li = [news.to_basic_dict() for news in collections]
    data = {
        'total_page': total_page,
        'current_page': current_page,
        'collections': collection_dict_li
    }
    return render_template('news/user_collection.html', data=data)


@profile_blue.route('/news_release', methods=['POST', 'GET'])
@user_login_data
def news_release():
    if request.method == 'GET':
        categories = list()

        try:
            # get all of category data
            categories = Category.query.all()
        except Exception as e:
            current_app.logger.error(e)

        categories_dicts = [category.to_dict() for category in categories]

        # remove 'up to date' in categories_dicts
        categories_dicts.pop(0)

        data = {
            'categories': categories_dicts
        }
        return render_template('news/user_news_release.html', data=data)

    # post and save data
    title = request.form.get('title')
    source = '个人发布'
    digest = request.form.get('digest')
    content = request.form.get('content')
    index_image = request.files.get('index_image')
    category_id = request.form.get('category_id')

    # verify params
    if not all([title, source, digest, content, index_image, category_id]):
        return jsonify(error=RET.PARAMERR, errmsg='params is not full')

    # get image
    try:
        index_image = index_image.read()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(error=RET.PARAMERR, errmsg='image is not true')

    # save image to qiniu
    try:
        key = storage(index_image)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(error=RET.THIRDERR, errmsg='upload image failed')

    # init news
    new = News()
    new.title = title
    new.digest = digest
    new.source = source
    new.content = content
    new.index_image_url = constants.QINIU_DOMIN_PREFIX + key
    new.category_id = category_id
    new.user_id = g.user.id
    # 1 instead of under review
    new.status = 1

    # save new
    try:
        db.session.add(new)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(error=RET.DBERR, errmsg='save data failed')

    # return response
    return jsonify(error=RET.OK, errmsg='upload success,wait for reviewing')


@profile_blue.route('/news_list')
@user_login_data
def news_list():
    # get page
    page = request.args.get('page', 1)

    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        page = 1

    user = g.user
    news_li = list()
    current_page = 1
    total_page = 1

    try:
        paginate = News.query.filter(News.user_id == user.id).paginate(page, constants.USER_COLLECTION_MAX_NEWS, False)
        # get current page data
        news_li = paginate.items
        # get current page
        current_page = paginate.page
        # get total page
        total_page = paginate.pages
    except Exception as e:
        current_app.logger.error(e)

    news_dict_li = [news_item.to_review_dict() for news_item in news_li]

    data = {
        'news_list': news_dict_li,
        'total_page': total_page,
        'current_page': current_page
    }

    return render_template('news/user_news_list.html', data=data)


@profile_blue.route('/user_follow')
@user_login_data
def user_follow():
    # get args of page
    page = request.args.get('page')

    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        page = 1

    user = g.user

    follows = list()
    current_page = 1
    total_page = 1

    try:
        paginate = user.followers.paginate(page, constants.USER_FOLLOWED_MAX_COUNT, False)
        follows = paginate.items
        current_page = paginate.page
        total_page = paginate.pages
    except Exception as e:
        current_app.logger.error(e)

    user_dict_li = [follow_user.to_dict() for follow_user in follows]

    data = {
        'users': user_dict_li,
        'total_page': total_page,
        'current_page': current_page
    }
    return render_template('news/user_follow.html', data=data)


@profile_blue.route('/other_info')
@user_login_data
def other_info():
    """query user infomations"""
    user = g.user

    # get other people id
    user_id = request.args.get("id")
    if not user_id:
        abort(404)

    # query user model
    other = None
    try:
        other = User.query.get(user_id)
    except Exception as e:
        current_app.logger.error(e)

    if not other:
        abort(404)

    # verify followed
    is_followed = False
    if g.user:
        if other.followers.filter(User.id == user.id).count() > 0:
            is_followed = True

    data = {
        "user_info": user.to_dict(),
        "other_info": other.to_dict(),
        "is_followed": is_followed
    }
    return render_template('news/other.html', data=data)


@profile_blue.route('/other_news_list')
def other_news_list():
    # 获取页数
    page = request.args.get("page", 1)
    user_id = request.args.get("user_id")
    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        page = 1

    if not all([page, user_id]):
        return jsonify(errno=RET.PARAMERR, errmsg="params error")

    try:
        user = User.query.get(user_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="query error")

    if not user:
        return jsonify(errno=RET.NODATA, errmsg="user is not login")

    try:
        paginate = News.query.filter(News.user_id == user.id).paginate(page, constants.OTHER_NEWS_PAGE_MAX_COUNT, False)
        news_li = paginate.items
        current_page = paginate.page
        total_page = paginate.pages
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="query databases failed")

    news_dict_li = []

    for news_item in news_li:
        news_dict_li.append(news_item.to_review_dict())
    data = {"news_list": news_dict_li, "total_page": total_page, "current_page": current_page}
    return jsonify(errno=RET.OK, errmsg="OK", data=data)
