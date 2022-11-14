import datetime

import httpx
from multiprocessing.pool import ThreadPool

from flask import Flask, render_template
from asgiref.wsgi import WsgiToAsgi

app = Flask(__name__)

instances = {
    'qdon.space',
    'planet.moe',
    'ani.work',
    'social.silicon.moe',
    'kurry.social',
    'twingyeo.kr',
    'bunbers.org',
    'toot.funami.tech',
    'mstdn.jbc.ne.kr',
    'uri.life',
    'parfait.day',
}

statuses = {
    instance: {
        'alive': False,
        'users': 0,
        'registrations': False,
        'approval_required': False,
    }
    for instance in instances
}

last_updated = datetime.datetime.now()


def update_status(force=False):
    global last_updated
    if (datetime.datetime.now() - last_updated).total_seconds() < 60 and force is False:
        return

    pool = ThreadPool(10)

    pool.map(update_status_for_instance, instances)
    last_updated = datetime.datetime.now()


def update_status_for_instance(instance: str):
    global statuses

    print(instance)
    try:
        data = httpx.get(f'https://{instance}/api/v1/instance').json()
        statuses[instance]['users'] = data['stats']['user_count']
        statuses[instance]['registrations'] = data['registrations']
        statuses[instance]['approval_required'] = data['approval_required']
        statuses[instance]['alive'] = True
    except httpx.HTTPError:
        statuses[instance]['alive'] = False
    except Exception:
        statuses[instance]['alive'] = False


@app.route('/')
def index():
    update_status()
    # render statuses with template

    sorted_statuses = sorted(
        statuses.items(),
        key=lambda x: (
            x[1]['alive'],
            x[1]['registrations'],
            not x[1]['approval_required'],
            -x[1]['users']
        ),
        reverse=True)
    return render_template('index.html', statuses=sorted_statuses)


update_status(force=True)
asgi = WsgiToAsgi(app)
