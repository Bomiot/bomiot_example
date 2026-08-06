from bomiot.server.core.message import msg_message_return, detail_message_return, login_message_return, others_message_return
from bomiot.server.core.models import Customer
from bomiot.server.core.utils import all_fields_empty


def create_customer_process(data):
    """
    Process for creating customer.
    """
    language = data.get('request').META.get('HTTP_LANGUAGE', 'en-US')
    customer_check = Customer.objects.filter(data__name=data.get('data').get('name'),
                                             data__department=data.get('request').auth.department,
                                             is_delete=False).first()
    if customer_check is not None:
        return detail_message_return(language, "Customer already exists")
    return msg_message_return(language, "Success Create")


def update_customer_process(data):
    """
    Process for updating customer.
    """
    language = data.get('request').META.get('HTTP_LANGUAGE', 'en-US')
    update_field_check = all_fields_empty(data.get('updated_fields'))
    if update_field_check is False:
        customer_check = Customer.objects.filter(data__name=data.get('data').get('name'),
                                                 data__department=data.get('request').auth.department,
                                                 is_delete=False).exclude(id=data.get('data').get('id')).first()
        if customer_check is not None:
            return detail_message_return(language, "Customer already exists")
    return msg_message_return(language, "Success Update")


def delete_customer_process(data):
    """
    Process for updating customer.
    """
    language = data.get('request').META.get('HTTP_LANGUAGE', 'en-US')
    customer_check = Customer.objects.filter(id=data.get('data').get('id'),
                                       data__department=data.get('request').auth.department,
                                       is_delete=False).first()
    if customer_check is None:
        return detail_message_return(language, "Customer does not exists")
    return msg_message_return(language, "Success Delete")