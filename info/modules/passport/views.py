import re
import random
from datetime import datetime

from info.libs.yuntongxun.sms import CCP
from info.models import User
from . import passport_blue
from info import redis_store, db
from info.utils.captcha.captcha import captcha
from info.utils.response_code import RET
from flask import render_template, request, current_app, make_response, jsonify, session
from info import constants


@passport_blue.route('/image_code')
def get_image_code():
    # 1.request args of id
    image_code_id = request.args.get('code_id')
    # 2.create image code content
    name, text, image_data = captcha.generate_captcha()
    # 3.save in redis
    try:
        redis_store.set('image_code_id_' + image_code_id, text, constants.IMAGE_CODE_REDIS_EXPIRES)
    except Exception as e:
        current_app.logger.error(e)
        return make_response(jsonify(error=RET.DATAERR, errmsg='保存验证码失败'))

    resp = make_response(image_data)

    resp.headers['Content-Type'] = 'image/jpg'
    # 4.return image
    return image_data


@passport_blue.route('/smscode', methods=['POST'])
def sms_code():
    params_dict = request.json
    # 1.get mobile number infomation
    mobile = params_dict.get('mobile')
    # 2.get image code infomation
    image_code = params_dict.get('image_code')
    # 3.get code id infomation
    image_code_id = params_dict.get('image_code_id')
    # 4.verify all infomations
    if not all([mobile, image_code, image_code_id]):
        return jsonify(error=RET.PARAMERR, errmsg='参数不全')
    # 5.verify mobile number is true or false
    if not re.match(r'^1[3-9][0-9]{9}', mobile):
        return jsonify(error=RET.DATAERR, errmsg='手机号码不正确')
    # 6.verify image code
    real_image_code = None
    try:
        real_image_code = redis_store.get('image_code_id_' + image_code_id)
        if real_image_code:
            # to decode infomations from redis
            real_image_code = real_image_code.decode()
            redis_store.delete('image_code_id_' + image_code_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(error=RET.DBERR, errmsg='验证码查询错误')

    if not real_image_code:
        return jsonify(error=RET.NODATA, errmsg='验证码已过期')

    if image_code.lower() != real_image_code.lower():
        return jsonify(error=RET.DATAERR, errmsg='验证码输入错误')

    try:
        user = User.query.filter_by(mobile=mobile).first()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(error=RET.DBERR, errmsg='数据查询错误')
    if user:
        return jsonify(error=RET.DATAEXIST, errmsg='用户已存在，不能重复注册')
    # 7.create sms and send it to the mobile num
    result = random.randint(0, 999999)
    current_app.logger.info(result)
    sms_code = '%06d' % result
    current_app.logger.debug('sms image code content %s' % sms_code)

    # result = CCP().send_template_sms(mobile, [sms_code, constants.SMS_CODE_REDIS_EXPIRES / 60], '1')
    # if result != 0:
    #     return jsonify(error=RET.THIRDERR, errmsg='send sms failed')

    # 8.save sms to redis
    try:
        redis_store.set('SMS_' + mobile, sms_code, constants.SMS_CODE_REDIS_EXPIRES)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(error=RET.DBERR, errmsg='报错短信验证码失败')

    # 9.reutrn response
    return jsonify(error=RET.OK, errmsg='ok')


@passport_blue.route('/register', methods=['POST'])
def register():
    """
    register user to database
    we need three parmas mobile numble，sms code and password
    """
    data = request.json
    # get mobile , sms code and password
    mobile = data.get('mobile')
    sms_code = data.get('smscode')
    password = data.get('password')

    # if not all params
    if not all([mobile, sms_code, password]):
        return jsonify(error=RET.PARAMERR, errmsg='参数不全')

    # get real sms code from redis
    try:
        real_sms_code = redis_store.get('SMS_' + mobile)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(error=RET.DATAERR, errmsg='获取短信验证码失败')
    # determine sms whether None
    if not real_sms_code:
        return jsonify(RET.NODATA, errmsg='短信验证码已过期')
    # verify sms code whether true or false
    if sms_code != real_sms_code.decode():
        return jsonify(RET.DATAERR, errmsg='短信验证码错误')

    # verify true
    try:
        redis_store.delete('SMS_' + mobile)
    except Exception as e:
        current_app.logger.error(e)

    # init user model
    user = User()
    user.nick_name = mobile
    user.mobile = mobile
    # password encryption
    user.password = password

    # storage user
    try:
        db.session.add(user)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(e)
        return jsonify(RET.DATAERR, errmsg='用户保存错误')

    # keep login in web clent
    session['user_id'] = user.id
    session['nick_name'] = user.nick_name
    session['mobile'] = user.mobile

    # return response
    return jsonify(error=RET.OK, errmsg='ok')


@passport_blue.route('/login', methods=['POST'])
def login():
    """
    login api
    need mobile and passworld
    """
    # get parmas and detemine if there is a value
    data = request.json
    mobile = data.get('mobile')
    password = data.get('password')

    # verify params
    if not all([mobile, password]):
        return jsonify(error=RET.PARAMERR, errmsg='参数不全')

    # find user from database of user table
    try:
        user = User.query.filter_by(mobile=mobile).first()
    except Exception as e:
        current_app.logger.info(e)
        return jsonify(error=RET.DATAERR, errmsg='用户查询错误')
    # if not have user
    if not user:
        return jsonify(error=RET.DATAEXIST, errmsg='用户不存在')

    # verify password
    if not user.check_passowrd(password):
        return jsonify(error=RET.PWDERR, errmsg='用户名或密码错误')

    # login success save user infomations in session
    session['user_id'] = user.id
    session['nick_name'] = user.nick_name
    session['mobile'] = user.mobile
    # recording last login time
    user.last_login = datetime.now()
    # submit user infomations update
    try:
        db.session.commit()
    except Exception as e:
        current_app.error(e)
        return jsonify(error=RET.DATAERR, errmsg='用户数据更新错误')

    return jsonify(error=RET.OK, errmsg='ok')


@passport_blue.route('/logout', methods=['POST'])
def logout():
    """
    logout API
    clear data from session
    """
    session.pop('user_id', None)
    session.pop('nick_name', None)
    session.pop('mobile', None)

    # return response
    return jsonify(error=RET.OK, errmsg='ok')
