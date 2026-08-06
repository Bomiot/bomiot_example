from bomiot.server.core.message import msg_message_return, detail_message_return, login_message_return, others_message_return
from bomiot.server.core.models import Customer
from bomiot.server.core.utils import merge_and_filter_items
from bomiot.server.core.utils import all_fields_empty
from django.contrib.auth import get_user_model
from bomiot.server.core.models import ASNDetail
from bomiot.server.core.models import Stock

User = get_user_model()


def asn_status_1_process(data):
    """
    Process for asn status 1.
    """
    language = data.get('request').META.get('HTTP_LANGUAGE', 'en-US')
    data.get('data')['status'] = 1
    data.get('data')['detail'] = merge_and_filter_items(data.get('data')['detail'])
    for i in data.get('data')['detail']:
        asn_detail = {
            'asn_id': data.get('data').get('asn_id'),
            'goods_code': i.get('selected').get('label'),
            'goods_name': i.get('selected').get('name'),
            'asn_qty': float(i.get('qty')),
            'shelving_qty': 0,
            'department': data.get('request').auth.department,
            'status': 1,
        }
        ASNDetail.objects.create(data=asn_detail, project=data.get('request').META.get('HTTP_PROJECT', 'bomiot'))
        
        stock_exist = Stock.objects.filter(data__goods_code=i.get('selected').get('label'),
                                           data__department=data.get('request').auth.department,
                                           project=data.get('request').META.get('HTTP_PROJECT', 'bomiot'))
        if stock_exist.exists():
            stock_list = stock_exist.first()
            stock_data_list = stock_list.data
            stock_data_list['total_qty'] = float(stock_data_list.get('total_qty', 0)) + float(i.get('qty'))
            stock_data_list['asn_qty'] = float(stock_data_list.get('asn_qty', 0)) + float(i.get('qty'))
            stock_list.data = stock_data_list
            stock_list.save()
        else:
            stock_detail = {
                'goods_code': i.get('selected').get('label'),
                'goods_name': i.get('selected').get('name'),
                'total_qty': float(i.get('qty')),
                'on_hand_qty': 0,
                'can_use_qty': 0,
                'hold_qty': 0,
                'inspection_qty': 0,
                'damage_qty': 0,
                'allocated_qty': 0,
                'asn_qty': float(i.get('qty')),
                'dn_qty': 0,
                'department': data.get('request').auth.department,
            }
            Stock.objects.create(data=stock_detail, project=data.get('request').META.get('HTTP_PROJECT', 'bomiot'))
    data.get('data').pop('detail', None)
    return msg_message_return(language, "Success Create")