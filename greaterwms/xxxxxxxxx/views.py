from django.contrib.auth import get_user_model
from django.http import JsonResponse

User = get_user_model()

async def test(request):
    return JsonResponse({"msg": "This is Django APP test API!!!"})