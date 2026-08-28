import json
from datetime import datetime, timedelta
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from greaterwms.auth.models import AuthModel

User = get_user_model()

async def auth_check(request):
    authed = request.META.get('HTTP_AUTHED') or request.headers.get('Authed') or request.headers.get('authed')
    print(authed)
    if not authed:
        return JsonResponse({"error": "Missing Authed header"}, status=403)
    if str(authed).strip() != 'Bomiot':
        return JsonResponse({"error": "Invalid Authed header"}, status=403)

    body = request.body
    try:
        payload = json.loads(body) if body else None
    except json.JSONDecodeError as e:
        payload = None
    print("[auth.views.test] POST JSON payload:", payload)

    if not isinstance(payload, dict):
        return JsonResponse({"error": "Invalid JSON body"}, status=400)

    community_key = payload.get('COMMUNITY_KEY') or payload.get('community_key')
    sponsor_key = payload.get('SPONSOR_KEY') or payload.get('sponsor_key')

    if not community_key or not sponsor_key:
        return JsonResponse({"error": "COMMUNITY_KEY and SPONSOR_KEY are required"}, status=400)

    try:
        record = AuthModel.objects.using('default').filter(
            community_key=community_key,
            sponsor_key=sponsor_key
        ).first()
    except Exception as exc:
        print("[auth.views.test] DB query error:", exc)
        record = None

    if record is not None and record.expired is not None:
        expired_dt = record.expired
    else:
        expired_dt = datetime.now() + timedelta(days=7)
        try:
            if record is None:
                AuthModel.objects.using('default').create(
                    community_key=community_key,
                    sponsor_key=sponsor_key,
                    expired=expired_dt,
                )
            else:
                record.expired = expired_dt
                record.save(using='default')
        except Exception as exc:
            print("[auth.views.test] DB create/save error:", exc)

    expired_ts = int(expired_dt.timestamp())
    print({"expired": expired_ts})
    return JsonResponse({"expired": expired_ts})