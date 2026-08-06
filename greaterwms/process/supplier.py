from bomiot.server.core.message import msg_message_return, detail_message_return, login_message_return, others_message_return
from bomiot.server.core.models import Supplier
from bomiot.server.core.utils import all_fields_empty
from django.contrib.auth import get_user_model

User = get_user_model()


def create_supplier_process(data):
    """
    Process for creating supplier.
    """
    language = data.get('request').META.get('HTTP_LANGUAGE', 'en-US')
    supplier_check = Supplier.objects.filter(data__name=data.get('data').get('name'),
                                             data__department=data.get('request').auth.department,
                                             is_delete=False).first()
    if supplier_check is not None:
        return detail_message_return(language, "Supplier already exists")
    return msg_message_return(language, "Success Create")


def update_supplier_process(data):
    """
    Process for updating supplier.
    """
    language = data.get('request').META.get('HTTP_LANGUAGE', 'en-US')
    update_field_check = all_fields_empty(data.get('updated_fields'))
    if update_field_check is False:
        supplier_check = Supplier.objects.filter(data__name=data.get('data').get('name'),
                                                 data__department=data.get('request').auth.department,
                                                 is_delete=False).exclude(id=data.get('data').get('id')).first()
        if supplier_check is not None:
            return detail_message_return(language, "Supplier already exists")
    return msg_message_return(language, "Success Update")


def delete_supplier_process(data):
    """
    Process for updating supplier.
    """
    language = data.get('request').META.get('HTTP_LANGUAGE', 'en-US')
    supplier_check = Supplier.objects.filter(id=data.get('data').get('id'),
                                       data__department=data.get('request').auth.department,
                                       is_delete=False).first()
    if supplier_check is None:
        return detail_message_return(language, "Supplier does not exists")
    return msg_message_return(language, "Success Delete")