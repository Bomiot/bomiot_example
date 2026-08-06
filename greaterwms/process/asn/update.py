from bomiot.server.core.message import msg_message_return, detail_message_return, login_message_return, others_message_return
from bomiot.server.core.models import Customer
from bomiot.server.core.utils import merge_and_filter_items
from bomiot.server.core.utils import all_fields_empty
from django.contrib.auth import get_user_model
from bomiot.server.core.models import ASNDetail

User = get_user_model()


def asn_update_process(data):
    """
    Process for asn update.
    """
    language = data.get('request').META.get('HTTP_LANGUAGE', 'en-US')
    update_field_check = all_fields_empty(data.get('updated_fields'))
    if update_field_check is False:
        updated_fields_data = data.get('updated_fields').get('detail')
        ASNDetail.objects.filter(data__asn_id=data.get('data').get('asn_id')).delete()
        data.get('data')['detail'] = merge_and_filter_items(data.get('data')['detail'])
        for i in data.get('data')['detail']:
            asn_detail = {
                'asn_id': data.get('data').get('asn_id'),
                'goods_code': i.get('selected').get('label'),
                'goods_name': i.get('selected').get('name'),
                'qty': float(i.get('qty')),
                'department': data.get('request').auth.department,
                'status': 1,
            }
            ASNDetail.objects.create(data=asn_detail)
    return msg_message_return(language, "Success Update")