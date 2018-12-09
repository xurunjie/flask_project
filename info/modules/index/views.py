from info import redis_store
from . import index_blue


@index_blue.route('/')
def hello_world():
    redis_store.set('name', 'itheima')

    return '123'
