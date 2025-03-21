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
data_app_list = []

def orbitar_login(request):
    client = WebApplicationClient(settings.ORBITAR_CLIENT_ID)
    state = secrets.token_urlsafe(16) #генерируем state
    request.session['oauth_state'] = state #сохраняем state в сессию
    authorization_url = client.prepare_request_uri(
        settings.ORBITAR_AUTHORIZATION_URL,
        redirect_uri=request.build_absolute_uri('/callback_orbitar'),
        scope=['feed', 'vote:list'],
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
        'page': 1,
        'perpage': 50,
        'format': 'html',
    }
    response = requests.post(settings.ORBITAR_FEED_ALL_URL, headers=headers, json=data)

    if response.status_code == 200:
        feed_data = response.json()
        posts = feed_data['payload']['posts']  # Получаем список постов

        # Преобразуем данные в список словарей, как в предыдущем примере
        data_app = []
        for item in posts:
            id = item['id']
            if item['site'] == 'main':
                link = 'https://orbitar.space/p' + str(id)
            else:
                link = 'https://orbitar.space/s/' + item['site'] + '/p' + str(id)
            try:
                title = item['title']
            except Exception:
                title = 'No Title'
                continue
            author = item['author']
            created = item['created']
            sub_orbit = item['site']
            post_id = None
            try:
                post_id = item['id']
            except KeyError:
                pass
            rating = item['rating']
            comments = item['comments']  # Добавляем комментарии

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

        # Получаем параметр sort_by из запроса
        sort_by = request.GET.get('sort_by')

        # Сортируем список data_app в зависимости от параметра sort_by
        if sort_by == 'comments_max':
            data_app = comments_max_sort(data_app)
        elif sort_by == 'rating_max':
            data_app = rating_max_sort(data_app)
        elif sort_by == 'rating_min':
            data_app = rating_min_sort(data_app)

        return render(request, 'probe_app/orbitar_all_feed_posts.html', {'posts': data_app})
    else:
        return render(request, 'probe_app/orbitar_all_feed_posts.html', {'error': f'Ошибка при получении последней страницы: {response.text}'})


def _get_voites(ids):
    token = OrbitarToken.objects.latest('expires_at')
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {token.access_token}',
    }
    id_votes = {}
    for id in ids:
        data = {
            'type': 'post',
            'id': f'{id}',  
        }
        print(id)
        response = requests.post(settings.ORBITAR_VOTES_LIST, headers=headers, json=data)


        if response.status_code == 200:
            votes_data = response.json()
            list_votes = [item['vote'] for item in votes_data['payload']['votes']]
            total_votes = _summ_votes(list_votes)
            print(total_votes)
            try:
                id_votes[id] = total_votes
            except Exception as err:
                id_votes[id] = 'None'
                pass
    print(id_votes)
    return id_votes

def _summ_votes(list_votes):
    sum = 0 
    try:
        for i in list_votes:
            sum = sum + i
    except TypeError:
        pass
    return sum

def comments_max_sort(data_app):
    """Сортирует список словарей по убыванию количества комментариев."""
    data_app.sort(key=lambda item: item['comments'], reverse=True)
    return data_app

def rating_max_sort(data_app):
    """Сортирует список словарей по убыванию рейтинга."""
    data_app.sort(key=lambda item: item['rating'], reverse=True)
    return data_app

def rating_min_sort(data_app):
    """Сортирует список словарей по возрастанию рейтинга."""
    data_app.sort(key=lambda item: item['rating'])
    return data_app