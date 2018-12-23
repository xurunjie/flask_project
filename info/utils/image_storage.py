from flask import current_app
from qiniu import Auth, put_data

access_key = 'bWsi94eq04NNL9I7Zud3iJY6q3DRTeagdY4wlmmD'
secret_key = 'FEctBOVDYcZKNCe0tyF2yF1dJCw4CxipXU0zRStF'


# 有一个函数执行添加的操作
def storage(data):
    # 构建鉴权对象 --> 网络请求
    try:
        q = Auth(access_key, secret_key)
    except Exception as e:
        current_app.logger.error(e)
        raise e

    # 要上传的空间
    bucket_name = 'xiezhou'

    # 生成上传 Token，可以指定过期时间等
    # 文件名可以不传, 服务器可以帮我们自动生成
    token = q.upload_token(bucket_name, None, 3600)

    ret, info = put_data(token, None, data)
    if info.status_code != 200:
        raise Exception('上传图片失败')
    print(info)
    print(ret)
    return ret['key']


if __name__ == '__main__':
    file = input('请输入文件路径')
    with open(file, 'rb') as f:
        storage(f.read())