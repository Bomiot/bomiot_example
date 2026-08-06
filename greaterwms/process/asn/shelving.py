from bomiot.server.core.message import msg_message_return, detail_message_return, login_message_return, others_message_return
from bomiot.server.core.models import Customer
from bomiot.server.core.utils import merge_and_filter_items
from bomiot.server.core.utils import all_fields_empty
from django.contrib.auth import get_user_model
from bomiot.server.core.models import ASN, ASNDetail, Bin, Stock, StockBin

User = get_user_model()

property_list = ['Normal', 'Hold', 'Damage', 'Inspection']

def stock_shelving(data):
    """
    Process for asn detail shelving to bin.
    """
    language = data.get('request').META.get('HTTP_LANGUAGE', 'en-US')
    project = data.get('request').META.get('HTTP_PROJECT', 'bomiot')
    shelving_to_bin = data.get('data').get('selected').get('label')
    asn_id = data.get('data').get('asn_id')
    goods_code = data.get('data').get('goods_code')
    qty = float(data.get('data').get('qty', 0))
    bin_property = Bin.objects.filter(data__name=shelving_to_bin, project=project, is_delete=False).first().data.get('property', 'Normal')
    asn_status_change_data = ASN.objects.filter(data__asn_id=asn_id, project=project, is_delete=False).first()
    asn_status_change_data.data['status'] = 2
    stock_list = Stock.objects.filter(data__goods_code=goods_code, project=project, is_delete=False).first()
    stock_list.data['asn_qty'] = stock_list.data.get('asn_qty', 0) - qty
    stock_list.data['on_hand_qty'] = stock_list.data.get('on_hand_qty', 0) + qty
    if bin_property == 'Normal':
        stock_list.data['can_use_qty'] = stock_list.data.get('can_use_qty', 0) + qty
    if bin_property == 'Hold':
        stock_list.data['hold_qty'] = stock_list.data.get('hold_qty', 0) + qty
    if bin_property == 'Damage':
        stock_list.data['damage_qty'] = stock_list.data.get('damage_qty', 0) + qty
    if bin_property == 'Inspection':
        stock_list.data['inspection_qty'] = stock_list.data.get('inspection_qty', 0) + qty
    stock_bin_data = {
        'bin_name': shelving_to_bin,
        'goods_code': goods_code,
        'goods_name': data.get('data').get('goods_name'),
        'on_hand_qty': qty,
        'allocated_qty': 0,
        'department': data.get('request').auth.department,
    }
    StockBin.objects.create(data=stock_bin_data,
                            project=project)
    stock_list.save()
    asn_status_change_data.save()
    data.get('data')['shelving_qty'] = data.get('data')['shelving_qty'] + qty
    data.get('data').pop('process', None)
    data.get('data').pop('selected', None)
    data.get('data').pop('qty', None)
    return msg_message_return(language, "Success Update")