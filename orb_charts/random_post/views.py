import random
import requests
import json
from datetime import datetime, timedelta
from django.conf import settings
from django.shortcuts import render
from django.utils import timezone
from django.utils import timezone as dj_timezone
import base64
from django.contrib.auth.decorators import login_required

from probe_app.models import OrbitarToken

base_url = 'https://orbitar.space/'

def refresh_orbitar_token(token):
    #делаем expires_at aware, если он naive
    if dj_timezone.is_naive(token.expires_at):
        expires_at_aware = dj_timezone.make_aware(token.expires_at, timezone.utc)
    else:
        expires_at_aware = token.expires_at

    if expires_at_aware > dj_timezone.now():
        return token #токен еще валиден

    if not token.refresh_token:
        return None #нет refresh token, надо логиниться

    client_id = settings.ORBITAR_CLIENT_ID
    client_secret = settings.ORBITAR_CLIENT_SECRET
    auth_string = f"{client_id}:{client_secret}"
    auth_bytes = auth_string.encode("ascii")
    auth_base64 = base64.b64encode(auth_bytes).decode("ascii")

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {auth_base64}",
    }

    data = {
        "grant_type": "refresh_token",
        "refresh_token": token.refresh_token,
    }

    response = requests.post(settings.ORBITAR_TOKEN_URL, headers=headers, data=data)

    if response.status_code == 200:
        token_data = response.json()
        expires_at = dj_timezone.now() + timedelta(seconds=token_data['expires_in'])

        token.access_token = token_data['access_token']
        token.refresh_token = token_data.get('refresh_token', token.refresh_token) #обновляем refresh токен, если он есть в ответе
        token.expires_at = expires_at
        token.save()
        return token
    else:
        return None #ошибка обновления токена


@login_required(login_url='/callback_orbitar/')
def random_post(request):
    
    try:
        token = OrbitarToken.objects.latest('expires_at') #получаем последний токен
    except OrbitarToken.DoesNotExist:
        return redirect('/orbitar_login') #если токенов нет, логинимся

    token = refresh_orbitar_token(token) #обновляем токен, если надо

    if not token:
        return redirect('/orbitar_login') #если токен не обновился, логинимся заново

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {token.access_token}',
    }
    data = {
        'page': 1,
        'perpage': 1,
        'format': 'html',
    }
    response = requests.post(settings.ORBITAR_FEED_ALL_URL, headers=headers, json=data)

    if response.status_code == 200:
        try:
            feed_data = response.json()
            posts = feed_data['payload']['posts']

            try:
                post_id = posts[0]['id']
                last_id = post_id
            except KeyError:
                post_id = None
                pass

        except Exception as e:
            print('Ошибка ' +  f'{e}')
            pass
        random_post_id = get_random_id(last_id)
        return _get_post(request, random_post_id) # Передаем request
    else:
        return render(request, 'random_post/random_post.html', {'error': f'Ошибка при получении данных: {response.status_code} - {response.text}'})

def get_random_id(last_id):
    return random.randrange(2, last_id)

def _get_post(request, post_id): # Добавляем request как аргумент
    try:
        token = OrbitarToken.objects.latest('expires_at')
    except OrbitarToken.DoesNotExist:
        return render(request, 'random_post/random_post.html', {'error': 'Токен не найден. Войдите в систему.'})

    now = timezone.now()
    if timezone.is_naive(token.expires_at):
        expires_at = timezone.make_aware(token.expires_at, timezone.utc)
    else:
        expires_at = token.expires_at

    if expires_at < now:
        return render(request, 'random_post/random_post.html', {'error': 'Срок действия токена истек. Войдите в систему.'})

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {token.access_token}',
    }
    data = {
        'id': post_id,
        'format': 'html',
    }
    response = requests.post('https://api.orbitar.space/api/v1/post/get', headers=headers, json=data) # Исправляем URL

    if response.status_code == 200:
        try:
            feed_data = response.json()
            post = feed_data['payload']['post']
            print(post)
            data_app = []

            try:
                post_id = post['id']
            except KeyError:
                post_id = None
                pass
            sub_orb = post['site']
            created = post['created']
            if post['title']:
                title = post['title']
            else:
                title = 'No Title'
            rating = post['rating']
            content = post['content']
            link = _create_link(base_url=base_url, post_id=post_id, site=sub_orb)
            data_app.append({
                'link': link,
                'post_id': str(post_id),
                'title': title,
                'created': created,
                'sub_orb': sub_orb,
                'rating': rating,
                'content': content

            })
            print(data_app[0])
            data_app = data_app[0]
            return render(request, 'random_post/random_post.html', {'post': data_app}) # Передаем request
        except (KeyError, json.JSONDecodeError) as e:
            return render(request, 'random_post/random_post.html', {'error': f'Ошибка обработки данных API: {e}'}) # Передаем request
    elif response.status_code == 401:
        return render(request, 'random_post/random_post.html', {'error': 'Ошибка авторизации. Токен недействителен.'}) # Передаем request
    else:
        return render(request, 'random_post/random_post.html', {'error': f'Ошибка при получении данных: {response.status_code} - {response.text}'}) # Передаем request

def _create_link(base_url, post_id, site):
    if site != 'main':
        link = base_url + 's/' + site + '/' + 'p' + str(post_id)
    else:
        link = base_url + 'p' + str(post_id)
    
    return link