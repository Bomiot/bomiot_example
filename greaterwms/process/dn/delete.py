from bomiot.server.core.message import msg_message_return, detail_message_return, login_message_return, others_message_return
from bomiot.server.core.models import Customer
from bomiot.server.core.utils import merge_and_filter_items
from bomiot.server.core.utils import all_fields_empty
from django.contrib.auth import get_user_model
from django.utils import timezone
from bomiot.server.core.models import DNDetail

User = get_user_model()


def dn_delete_process(data):
    """
    Process for DN update.
    """
    language = data.get('request').META.get('HTTP_LANGUAGE', 'en-US')
    DN_detail_list = DNDetail.objects.filter(data__dn_id=data.get('data').get('dn_id'), data__status=1)
    if DN_detail_list.exists() is False:
        return detail_message_return(language, "DN has details with status greater than 1, cannot delete.")
    DN_detail_list.update(is_delete=True, updated_time=timezone.now())
    return msg_message_return(language, "Success Delete")