import logging
import redis


class Config(object):
    """
    the object sets for flask object to know that which config should
    to import for the project
    """
    # params need to connect mysql databases
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:xu19951009@127.0.0.1/info'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # params need to connect redis databases
    REDIS_HSOT = '127.0.0.1'
    REDIS_PORT = 6379

    # set secret key
    SECRET_KEY = '+zcM2+aeq8deuvhscvgdlwex6slq9k1f3cj+o5ZbwRA='

    # set flask session extension
    SESSION_TYPE = 'redis'
    SESSION_REDIS = redis.StrictRedis(host=REDIS_HSOT, port=REDIS_PORT)
    SESSION_USE_SIGNER = True
    PERMANENT_SESSION_LIFETIME = 86400 * 7


class DevelopmentConfig(Config):
    # development environmention
    DEBUG = True
    LOG_LEVEL = logging.DEBUG


class ProductionConfig(Config):
    # product enviremention
    DEBUG = False
    LOG_LEVEL = logging.WARN
