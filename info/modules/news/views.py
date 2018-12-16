from flask import jsonify, session, current_app, render_template, g, abort, request

from info import constants, db
from info.models import User, News, Comment, CommentLike
from info.utils.response_code import RET
from . import news_blue
from info.utils.common import user_login_data


@news_blue.route('/<int:news_id>')
@user_login_data
def news_detail(news_id):
    news = None
    try:
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)
        abort(404)

    if not news:
        # retur not find
        abort(404)

    news.clicks += 1

    # click news list
    news_list = None
    try:
        news_list = News.query.order_by(News.clicks.desc()).limit(constants.CLICK_RANK_MAX_NEWS)
    except Exception as e:
        current_app.logger.error(e)

    click_news_list = []
    for news_item in news_list if news_list else []:
        click_news_list.append(news_item.to_dict())

    # is followed this author
    is_followed = False
    # this new is collected , yes or no
    is_collected = False
    user = g.user
    if user:
        if news in user.collection_news:
            is_collected = True

    if news.user and user:
        if news.user in user.followed:
            is_followed = True

    # get news comment
    comments = []
    try:
        comments = Comment.query.filter(Comment.news_id == news_id).order_by(Comment.create_time.desc()).all()
    except Exception as e:
        current_app.logger.error(e)

    comment_like_ids = []
    # get comment like info
    if g.user:
        # if user is not none
        try:
            comment_ids = [comment.id for comment in comments]
            if len(comment_ids) > 0:
                # get current user comment like list
                comment_likes = CommentLike.query.filter(CommentLike.comment_id.in_(comment_ids),
                                                         CommentLike.user_id == g.user.id).all()
                # get current user id
                comment_like_ids = [comment_like.comment_id for comment_like in comment_likes]
        except Exception as e:
            current_app.logger.error(e)

    comment_list = []
    for item in comments if comments else []:
        # comment_list.append(item.to_dict())
        comment_dict = item.to_dict()
        comment_dict["is_like"] = False
        # if current user like the news
        if g.user and item.id in comment_like_ids:
            comment_dict["is_like"] = True
        comment_list.append(comment_dict)

    data = {
        "click_news_list": click_news_list,
        "news": news.to_dict(),
        "user_info": g.user.to_dict() if g.user else None,
        "is_collected": is_collected,
        "comments": comment_list,
        "is_followed": is_followed
    }

    return render_template('news/detail.html', data=data)


@news_blue.route('/news_comment', methods=['POST'])
@user_login_data
def add_news_comment():
    """
    add comments
    """
    user = g.user
    if not user:
        return jsonify(error=RET.SERVERERR, errmsg='user is not login')
    # get params
    data = request.json
    news_id = data.get('news_id')
    comment_str = data.get('comment')
    parent_id = data.get('parent_id')
    # verify all params
    if not all([news_id, comment_str]):
        return jsonify(error=RET.PARAMERR, errmsg='params is not full')

    try:
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(error=RET.DBERR, errmsg='query data failed')

    if not news:
        return jsonify(error=RET.NODATA, errmsg='this new is not actived')

    # init model data for comment
    comment = Comment()
    comment.user_id = user.id
    comment.news_id = news_id
    comment.content = comment_str
    if parent_id:
        comment.parent_id = parent_id

    # save and commit
    try:
        db.session.add(comment)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(error=RET.DBERR, errmsg='save and comment this data failed')

    return jsonify(error=RET.OK, errmsg='comment commit success', data=comment.to_dict())
