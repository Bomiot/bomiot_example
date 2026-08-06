from bomiot.server.core.message import msg_message_return, detail_message_return, login_message_return, others_message_return
from bomiot.server.core.models import Goods
from bomiot.server.core.utils import all_fields_empty
from django.contrib.auth import get_user_model

User = get_user_model()


def create_googs_process(data):
    """
    Process for creating goods.
    """
    language = data.get('request').META.get('HTTP_LANGUAGE', 'en-US')
    user_info = User.objects.filter(id=data.get('request').auth.id).first()
    goods_check = Goods.objects.filter(data__code=data.get('data').get('code'),
                                       data__department=user_info.department,
                                       is_delete=False).first()
    if goods_check is not None:
        return detail_message_return(language, "Goods already exists")
    return msg_message_return(language, "Success Create")


def update_googs_process(data):
    """
    Process for updating goods.
    """
    language = data.get('request').META.get('HTTP_LANGUAGE', 'en-US')
    user_info = User.objects.filter(id=data.get('request').auth.id).first()
    update_field_check = all_fields_empty(data.get('updated_fields'))
    if update_field_check is False:
        goods_check = Goods.objects.filter(data__code=data.get('data').get('code'),
                                           data__department=user_info.department,
                                           is_delete=False).exclude(id=data.get('data').get('id')).first()
        if goods_check is not None:
            return detail_message_return(language, "Goods already exists")
    return msg_message_return(language, "Success Update")


def delete_googs_process(data):
    """
    Process for updating goods.
    """
    language = data.get('request').META.get('HTTP_LANGUAGE', 'en-US')
    user_info = User.objects.filter(id=data.get('request').auth.id).first()
    goods_check = Goods.objects.filter(id=data.get('data').get('id'),
                                       data__department=user_info.department,
                                       is_delete=False).first()
    if goods_check is None:
        return detail_message_return(language, "Goods does not exists")
    return msg_message_return(language, "Success Delete")