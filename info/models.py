from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

from info import constants
from . import db


class BaseModel(object):
    """base model to create to recording the create time and update time"""
    create_time = db.Column(db.DateTime, default=datetime.now)
    update_time = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)


# user collections model to set many to many relationship


tb_user_collection = db.Table(
    "info_user_collection",
    db.Column("user_id", db.Integer, db.ForeignKey("info_user.id"), primary_key=True),
    db.Column("news_id", db.Integer, db.ForeignKey("info_news.id"), primary_key=True),
    db.Column("create_time", db.DateTime, default=datetime.now)
)

tb_user_follows = db.Table(
    "info_user_fans",
    db.Column('follower_id', db.Integer, db.ForeignKey('info_user.id'), primary_key=True),
    db.Column('followed_id', db.Integer, db.ForeignKey('info_user.id'), primary_key=True)
)


class User(BaseModel, db.Model):
    """user"""
    __tablename__ = "info_user"

    id = db.Column(db.Integer, primary_key=True)
    nick_name = db.Column(db.String(32), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    mobile = db.Column(db.String(11), unique=True, nullable=False)
    avatar_url = db.Column(db.String(256))  # user image url
    last_login = db.Column(db.DateTime, default=datetime.now)
    is_admin = db.Column(db.Boolean, default=False)
    signature = db.Column(db.String(512))
    gender = db.Column(
        db.Enum(
            "MAN",  # man
            "WOMEN"  # women
        ),
        default="MAN")

    # collections news of the user to collect
    collection_news = db.relationship("News", secondary=tb_user_collection, lazy="dynamic")
    # back reference
    followers = db.relationship('User',
                                secondary=tb_user_follows,
                                primaryjoin=id == tb_user_follows.c.followed_id,
                                secondaryjoin=id == tb_user_follows.c.follower_id,
                                backref=db.backref('followed', lazy='dynamic'),
                                lazy='dynamic')

    # current user releases news
    news_list = db.relationship('News', backref='user', lazy='dynamic')

    @property
    def password(self):
        raise AttributeError("current property is not readable")

    @password.setter
    def password(self, value):
        self.password_hash = generate_password_hash(value)

    def check_passowrd(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        resp_dict = {
            "id": self.id,
            "nick_name": self.nick_name,
            "avatar_url": constants.QINIU_DOMIN_PREFIX + self.avatar_url if self.avatar_url else "",
            "mobile": self.mobile,
            "gender": self.gender if self.gender else "MAN",
            "signature": self.signature if self.signature else "",
            "followers_count": self.followers.count(),
            "news_count": self.news_list.count()
        }
        return resp_dict

    def to_admin_dict(self):
        resp_dict = {
            "id": self.id,
            "nick_name": self.nick_name,
            "mobile": self.mobile,
            "register": self.create_time.strftime("%Y-%m-%d %H:%M:%S"),
            "last_login": self.last_login.strftime("%Y-%m-%d %H:%M:%S"),
        }
        return resp_dict


class News(BaseModel, db.Model):
    """news"""
    __tablename__ = "info_news"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(256), nullable=False)  # new title
    source = db.Column(db.String(64), nullable=False)  # new source
    digest = db.Column(db.String(512), nullable=False)  # new digrst
    content = db.Column(db.Text, nullable=False)  # new content
    clicks = db.Column(db.Integer, default=0)  # look count
    index_image_url = db.Column(db.String(256))  # src image address
    category_id = db.Column(db.Integer, db.ForeignKey("info_category.id"))
    user_id = db.Column(db.Integer, db.ForeignKey("info_user.id"))  # user id
    status = db.Column(db.Integer,
                       default=0)  # current new is reviewed status. 0 as for success. 1 as for being reviewing.-1 as for can not failed.
    reason = db.Column(db.String(256))  # not pass reason，status = -1 use
    # current new all comments
    comments = db.relationship("Comment", lazy="dynamic")

    def to_review_dict(self):
        resp_dict = {
            "id": self.id,
            "title": self.title,
            "create_time": self.create_time.strftime("%Y-%m-%d %H:%M:%S"),
            "status": self.status,
            "reason": self.reason if self.reason else ""
        }
        return resp_dict

    def to_basic_dict(self):
        resp_dict = {
            "id": self.id,
            "title": self.title,
            "source": self.source,
            "digest": self.digest,
            "create_time": self.create_time.strftime("%Y-%m-%d %H:%M:%S"),
            "index_image_url": self.index_image_url,
            "clicks": self.clicks,
        }
        return resp_dict

    def to_dict(self):
        resp_dict = {
            "id": self.id,
            "title": self.title,
            "source": self.source,
            "digest": self.digest,
            "create_time": self.create_time.strftime("%Y-%m-%d %H:%M:%S"),
            "content": self.content,
            "comments_count": self.comments.count(),
            "clicks": self.clicks,
            "category": self.category.to_dict(),
            "index_image_url": self.index_image_url,
            "author": self.user.to_dict() if self.user else None
        }
        return resp_dict


class Comment(BaseModel, db.Model):
    """comment"""
    __tablename__ = "info_comment"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("info_user.id"), nullable=False)
    news_id = db.Column(db.Integer, db.ForeignKey("info_news.id"), nullable=False)
    content = db.Column(db.Text, nullable=False)  # comment infomation
    parent_id = db.Column(db.Integer, db.ForeignKey("info_comment.id"))
    parent = db.relationship("Comment", remote_side=[id])
    like_count = db.Column(db.Integer, default=0)

    def to_dict(self):
        resp_dict = {
            "id": self.id,
            "create_time": self.create_time.strftime("%Y-%m-%d %H:%M:%S"),
            "content": self.content,
            "parent": self.parent.to_dict() if self.parent else None,
            "user": User.query.get(self.user_id).to_dict(),
            "news_id": self.news_id,
            "like_count": self.like_count
        }
        return resp_dict


class CommentLike(BaseModel, db.Model):
    """commentlike"""
    __tablename__ = "info_comment_like"
    comment_id = db.Column("comment_id", db.Integer, db.ForeignKey("info_comment.id"), primary_key=True)
    user_id = db.Column("user_id", db.Integer, db.ForeignKey("info_user.id"), primary_key=True)


class Category(BaseModel, db.Model):
    """category"""
    __tablename__ = "info_category"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    news_list = db.relationship('News', backref='category', lazy='dynamic')

    def to_dict(self):
        resp_dict = {
            "id": self.id,
            "name": self.name
        }
        return resp_dict
