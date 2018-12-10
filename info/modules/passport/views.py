import re
import random

from info.libs.yuntongxun.sms import CCP
from info.models import User
from . import passport_blue
from info import redis_store
from info.utils.captcha.captcha import captcha
from info.utils.response_code import RET
from flask import render_template, request, current_app, make_response, jsonify
from info import constants


@passport_blue.route('/login')
def passport():
    return 'passport'


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
        return make_response(jsonify(error=RET.DATAERR, errmsg='save image code failed'))
    # 4.return image
    return image_data


@passport_blue.route('/smscode', methods=['POST'])
def sms_code():
    current_app.logger.info('123')
    params_dict = request.json
    # 1.get mobile number infomation
    mobile = params_dict.get('mobile')
    # 2.get image code infomation
    image_code = params_dict.get('image_code')
    # 3.get code id infomation
    image_code_id = params_dict.get('image_code_id')
    # 4.verify all infomations
    if not all([mobile, image_code, image_code_id]):
        return jsonify(error=RET.PARAMERR, errmsg='params do not full')
    # 5.verify mobile number is true or false
    if not re.match(r'^1[3-9][0-9]{9}', mobile):
        return jsonify(error=RET.DATAERR, errmsg='手机号不正确')
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
        return jsonify(error=RET.DBERR, errmsg='get image code from redis failed')

    if not real_image_code:
        return jsonify(error=RET.NODATA, errmsg='image code had been expired')

    if image_code.lower() != real_image_code.lower():
        return jsonify(error=RET.DATAERR, errmsg='verify image code is not samed to realy image code')

    try:
        user = User.query.filter_by(mobile=mobile).first()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(error=RET.DBERR, errmsg='database query error')
    if user:
        return jsonify(error=RET.DATAEXIST, errmsg='the mobile has been registered')
    # 7.create sms and send it to the mobile num
    result = random.randint(0, 999999)
    sms_code = '%06d' % result
    current_app.logger.debug('sms image code content %s' % sms_code)

    result = CCP().send_template_sms(mobile, [sms_code, constants.SMS_CODE_REDIS_EXPIRES / 60], '1')
    if result != 0:
        return jsonify(error=RET.THIRDERR, errmsg='send sms failed')

    # 8.save sms to redis
    try:
        redis_store.set('SMS_' + mobile, sms_code, constants.SMS_CODE_REDIS_EXPIRES)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(error=RET.DBERR, errmsg='save sms code failed')

    # 9.reutrn response
    return jsonify(error=RET.OK, errmsg='send sms ok')
