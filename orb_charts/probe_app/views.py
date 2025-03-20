import requests
from django.shortcuts import redirect, render
from django.conf import settings
from oauthlib.oauth2 import WebApplicationClient
from datetime import datetime, timedelta
from .models import OrbitarToken
import json
import secrets
import base64

ids = []  # Объявляем переменную ids на глобальном уровне


def orbitar_login(request):
    client = WebApplicationClient(settings.ORBITAR_CLIENT_ID)
    state = secrets.token_urlsafe(16) #генерируем state
    request.session['oauth_state'] = state #сохраняем state в сессию
    authorization_url = client.prepare_request_uri(
        settings.ORBITAR_AUTHORIZATION_URL,
        redirect_uri=request.build_absolute_uri('/callback_orbitar'),
        scope=['feed'],
        state=state, #добавляем state в запрос
    )
    return redirect(authorization_url)

def callback_orbitar(request):
    state = request.GET.get('state')
    if state != request.session.get('oauth_state'):
        return render(request, 'probe_app/orbitar_feed_posts.html', {'error': 'Неверный state'})
    del request.session['oauth_state']

    authorization_code = request.GET.get('code')  # Получаем код авторизации из ответа

    client_id = settings.ORBITAR_CLIENT_ID
    client_secret = settings.ORBITAR_CLIENT_SECRET
    auth_string = f"{client_id}:{client_secret}"
    auth_bytes = auth_string.encode("ascii")
    auth_base64 = base64.b64encode(auth_bytes).decode("ascii")

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {auth_base64}",
    }

    nonce = secrets.token_urlsafe(16)
    redirect_uri = request.build_absolute_uri('/callback_orbitar')

    data = {
        "grant_type": "authorization_code",
        "code": authorization_code,
        "nonce": nonce,
        "redirect_uri": redirect_uri,
    }

    response = requests.post(settings.ORBITAR_TOKEN_URL, headers=headers, data=data)

    if response.status_code == 200:
        token_data = response.json()
        expires_at = datetime.now() + timedelta(seconds=token_data['expires_in'])

        token = OrbitarToken(
            access_token=token_data['access_token'],
            refresh_token=token_data.get('refresh_token'),
            expires_at=expires_at,
        )
        token.save()
        print('token saved!')

        return redirect('/orbitar_all_feed_posts')
    else:
        return render(request, 'probe_app/orbitar_feed_posts.html', {'error': f'Ошибка при получении токена: {response.text}'})

# posts_ids = []
def orbitar_all_feed_posts(request):
    token = OrbitarToken.objects.latest('expires_at')
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {token.access_token}',
    }
    data = {
        'page': 1,      # Начнем с первой страницы
        'perpage': 20,  # Количество постов на странице
        'format': 'html', #формат ответа jso
    }
    response = requests.post(settings.ORBITAR_FEED_ALL_URL, headers=headers, json=data)


    if response.status_code == 200:
        feed_data = response.json()
        # print(type(feed_data))
        # print(feed_data)
        # for item in feed_data['payload']['posts']:
        #     print(item['id'])
        ids = [item['id'] for item in feed_data['payload']['posts']]
        print(ids)

        return render(request, 'probe_app/orbitar_all_feed_posts.html', {'posts': feed_data})

    else:
        return render(request, 'probe_app/orbitar_all_feed_posts.html', {'error': f'Ошибка при получении последней страницы: {response.text}'})
