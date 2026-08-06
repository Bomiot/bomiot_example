from bomiot.server.core.message import msg_message_return, detail_message_return, login_message_return
from bomiot.server.core.models import Example
from bomiot.server.core.utils import queryset_to_dict, dynamic_import_and_call
from django.core.cache import cache
from greaterwms.process.goods import create_googs_process, update_googs_process, delete_googs_process
from greaterwms.process.bin import get_bin_process, create_bin_process, update_bin_process, delete_bin_process
from greaterwms.process.supplier import create_supplier_process, update_supplier_process, delete_supplier_process
from greaterwms.process.customer import create_customer_process, update_customer_process, delete_customer_process
from greaterwms.process.asn.status_1 import asn_status_1_process
from greaterwms.process.asn.update import asn_update_process
from greaterwms.process.asn.delete import asn_delete_process
from greaterwms.process.dn.status_1 import dn_status_1_process
from greaterwms.process.dn.update import dn_update_process
from greaterwms.process.dn.delete import dn_delete_process
from greaterwms.process.asn.shelving import stock_shelving

class GoodsClass(object):
    def goods_create(self, data):
        context = create_googs_process(data)
        return context
    
    def goods_update(self, data):
        context = update_googs_process(data)
        return context
    
    def goods_delete(self, data):
        context = delete_googs_process(data)
        return context
    

class BinClass(object):
    def bin_get(self, data):
        context = get_bin_process(data)
        return context
            
    def bin_create(self, data):
        context = create_bin_process(data)
        return context
    
    def bin_update(self, data):
        context = update_bin_process(data)
        return context
    
    def bin_delete(self, data):
        context = delete_bin_process(data)
        return context
    
class SupplierClass(object):
    def supplier_create(self, data):
        context = create_supplier_process(data)
        return context
    
    def supplier_update(self, data):
        context = update_supplier_process(data)
        return context
    
    def supplier_delete(self, data):
        context = delete_supplier_process(data)
        return context
    

class CustomerClass(object):
    def customer_create(self, data):
        context = create_customer_process(data)
        return context
    
    def customer_update(self, data):
        context = update_customer_process(data)
        return context
    
    def customer_delete(self, data):
        context = delete_customer_process(data)
        return context
    

class ASNClass(object):
    def asn_create(self, data):
        context = asn_status_1_process(data)
        return context
    
    def asn_update(self, data):
        context = asn_update_process(data)
        return context
    
    def asn_delete(self, data):
        context = asn_delete_process(data)
        return context


class ASNDetailClass(object):
    def asn_detail_update(self, data):
        process = data.get('data').get('process', None)
        if process == 'shelving':
            context = stock_shelving(data)
            return  context


class DNClass(object):
    def dn_create(self, data):
        context = dn_status_1_process(data)
        return context
    
    def dn_update(self, data):
        context = dn_update_process(data)
        return context
    
    def dn_delete(self, data):
        context = dn_delete_process(data)
        return context