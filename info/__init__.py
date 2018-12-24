import redis
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, g, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
from flask_session import Session

# we can use db.init to set db again
from info.utils.common import user_login_data

db = SQLAlchemy()

redis_store = None


def setup_log(config_name):
    """config of log module"""

    # set log level we will to recording
    logging.basicConfig(level=config_name.LOG_LEVEL)
    # create log recording address and max bytes and backup count
    file_log_handler = RotatingFileHandler("logs/log", maxBytes=1024 * 1024 * 100, backupCount=10)
    # create format of log to recording as level/filename/lineno/message
    formatter = logging.Formatter('%(levelname)s %(filename)s:%(lineno)d %(message)s')
    # create log set formatting
    file_log_handler.setFormatter(formatter)
    # global log for the projcet
    logging.getLogger().addHandler(file_log_handler)


def create_app(config_name):
    app = Flask(__name__)
    # import config from the Config object
    app.config.from_object(config_name)
    # mount log to project
    setup_log(config_name)
    # connect mysql databases
    db.init_app(app)
    # connect redis databases and specified ip and port
    global redis_store
    redis_store = redis.StrictRedis(host=config_name.REDIS_HSOT, port=config_name.REDIS_PORT)
    # start CSRF protect
    CSRFProtect(app)
    from flask_wtf.csrf import generate_csrf
    # create csrf
    @app.after_request
    def after_request(response):
        csrf_token = generate_csrf()
        # pass a value by cookie to client
        response.set_cookie('csrf_token', csrf_token)
        return response

    # 404 error page
    @app.errorhandler(404)
    @user_login_data
    def page_not_found(e):
        user = g.user
        data = {
            'user_info': user.to_dict() if user else None
        }
        return render_template('news/404.html', data=data)

    from info.utils.common import do_index_class
    app.add_template_filter(do_index_class, "index_class")
    # create flask session extension
    Session(app)

    # register index blueprint
    from info.modules.index import index_blue
    app.register_blueprint(index_blue)

    # register passport blueprint
    from info.modules.passport import passport_blue
    app.register_blueprint(passport_blue)

    # register news blueprint
    from info.modules.news import news_blue
    app.register_blueprint(news_blue)

    # register userprofile
    from info.modules.profile import profile_blue
    app.register_blueprint(profile_blue)

    # register admin blueprint
    from info.modules.admin import admin_blue
    app.register_blueprint(admin_blue)

    return app
