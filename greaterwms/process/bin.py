import orjson
from bomiot.server.core.message import msg_message_return, detail_message_return, login_message_return, others_message_return
from bomiot.server.core.models import Bin
from bomiot.server.core.utils import all_fields_empty, find_keys_by_value
from django.conf import settings
from os.path import join, exists
from tomlkit import parse
from django.core.cache import cache


property_list = ['Normal', 'Hold', 'Damage', 'Inspection']


def property_detail_return(data, version) -> dict:
    property_message = cache.get("property_message", version=version)
    property_key = data.get('property')
    if isinstance(property_key, dict):
        return data
    data['property'] = property_message.get(property_key, data.get('property'))
    return data


def get_property_return_data(data, version) -> dict:
    property_message = cache.get("property_message", version=version)
    if data in property_message:
        return property_message.get(data)
    else:
        return data


def get_bin_process(data):
    """
    Process for getting Bin.
    """
    language = data.get('request').META.get('HTTP_LANGUAGE', 'en-US')   
    message_path = join(settings.LANGUAGE_DIR, language + '.toml')
    message_dict = {}
    if exists(message_path):
        with open(message_path, 'r', encoding='utf-8') as message:
            message_data = parse(message.read())
    message_dict = message_data['others']
    cache.set('property_message', orjson.loads(orjson.dumps(message_dict).decode("utf-8")), version=data.get('request').auth.id)
    property_data_list = list(map(lambda x: get_property_return_data(x, data.get('request').auth.id), property_list))
    callback_data_list = list(map(lambda y: property_detail_return(y, data.get('request').auth.id), data.get('data')))
    cache.delete('property_message', version=data.get('request').auth.id)
    return [
        ('property', property_data_list),
        ('results', callback_data_list),
    ]


def create_bin_process(data):
    """
    Process for creating Bin.
    """
    language = data.get('request').META.get('HTTP_LANGUAGE', 'en-US')
    message_path = join(settings.LANGUAGE_DIR, language + '.toml')
    if exists(message_path):
        with open(message_path, 'r', encoding='utf-8') as message:
            message_data = parse(message.read())
    data.get('data')['property'] = find_keys_by_value(message_data['others'], data.get('data').get('property'))[0]
    data.get('data')['empty'] = 0
    data.get('data')['lock'] = 0
    goods_check = Bin.objects.filter(data__name=data.get('data').get('name'),
                                     data__department=data.get('request').auth.department,
                                     is_delete=False).first()
    if goods_check is not None:
        return detail_message_return(language, "Bin already exists")
    return msg_message_return(language, "Success Create")


def update_bin_process(data):
    """
    Process for updating Bin.
    """
    language = data.get('request').META.get('HTTP_LANGUAGE', 'en-US')
    message_path = join(settings.LANGUAGE_DIR, language + '.toml')
    if exists(message_path):
        with open(message_path, 'r', encoding='utf-8') as message:
            message_data = parse(message.read())
    update_field_check = all_fields_empty(data.get('updated_fields'))
    if update_field_check is False:
        property_check = data.get('updated_fields').get('property', '')
        if property_check:
            data.get('data')['property'] = find_keys_by_value(message_data['others'], property_check[1])[0]
        goods_check = Bin.objects.filter(data__name=data.get('data').get('name'),
                                         data__department=data.get('request').auth.department,
                                         is_delete=False).exclude(id=data.get('data').get('id')).first()
        if goods_check is not None:
            return detail_message_return(language, "Bin already exists")
    return msg_message_return(language, "Success Update")


def delete_bin_process(data):
    """
    Process for updating Bin.
    """
    language = data.get('request').META.get('HTTP_LANGUAGE', 'en-US')
    goods_check = Bin.objects.filter(id=data.get('data').get('id'),
                                     data__department=data.get('request').auth.department,
                                     is_delete=False).first()
    if goods_check is None:
        return detail_message_return(language, "Bin does not exists")
    return msg_message_return(language, "Success Delete")