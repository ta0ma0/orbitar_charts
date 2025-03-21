import requests
from django.shortcuts import redirect, render
from django.conf import settings
from oauthlib.oauth2 import WebApplicationClient
from datetime import datetime, timedelta
from probe_app.models import OrbitarToken #модель токена из первого приложения
import json
import secrets
import base64
from django.utils import timezone

def random_post(request):
    try:
        token = OrbitarToken.objects.latest('expires_at')
    except OrbitarToken.DoesNotExist:
        return render(request, 'random_post/random_post.html', {'error': 'Токен не найден. Войдите в систему.'})

    now = timezone.now()
    if timezone.is_naive(token.expires_at):
        expires_at = timezone.make_aware(token.expires_at, timezone.get_current_timezone())
    else:
        expires_at = token.expires_at

    if expires_at < now:
        return render(request, 'random_post/random_post.html', {'error': 'Срок действия токена истек. Войдите в систему.'})

    try:
        token = OrbitarToken.objects.latest('expires_at')
    except OrbitarToken.DoesNotExist:
        return render(request, 'random_post/random_post.html', {'error': 'Токен не найден. Войдите в систему.'})

    if token.expires_at < datetime.now():
        return render(request, 'random_post/random_post.html', {'error': 'Срок действия токена истек. Войдите в систему.'})

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {token.access_token}',
    }
    data = {
        'page': 1,
        'perpage': 3,
        'format': 'html',
    }
    response = requests.post(settings.ORBITAR_FEED_ALL_URL, headers=headers, json=data)

    if response.status_code == 200:
        try:
            feed_data = response.json()
            posts = feed_data['payload']['posts']
            data_app = []
            for item in posts:
                # ... ваш код для обработки данных ...
                data_app.append({
                    'post_id': post_id,
                    'title': title,
                    'created': created,
                    'sub_orbit': sub_orbit,
                    'author': author,
                    'rating': rating,
                    'comments': comments,
                    'link': link,
                })
            return render(request, 'random_post/random_post.html', {'posts': data_app[0]})
        except (KeyError, json.JSONDecodeError) as e:
            return render(request, 'random_post/random_post.html', {'error': f'Ошибка обработки данных API: {e}'})
    elif response.status_code == 401:
        return render(request, 'random_post/random_post.html', {'error': 'Ошибка авторизации. Токен недействителен.'})
    else:
        return render(request, 'random_post/random_post.html', {'error': f'Ошибка при получении данных: {response.status_code} - {response.text}'})





