from flask import g, request, render_template

from . import profile_blue
from info.utils.common import user_login_data


@profile_blue.route('/base_info', methods=["POST", 'GET'])
@user_login_data
def base_info():
    """
    get user infomations
    """
    user = g.user
    if request.method == 'GET':
        pass
        # TODO next to tomorrow

