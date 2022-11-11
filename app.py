import datetime

import httpx

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
}

statuses = {
    instance: {
        'alive': False,
        'users': 0,
        'registrations': False,
    }
    for instance in instances
}

last_updated = datetime.datetime.now()


def update_status(force=False):
    global last_updated
    if (datetime.datetime.now() - last_updated).total_seconds() < 60 and force is False:
        return

    last_updated = datetime.datetime.now()
    for instance in instances:
        print(instance)
        try:
            data = httpx.get(f'https://{instance}/api/v1/instance').json()
            statuses[instance]['users'] = data['stats']['user_count']
            statuses[instance]['registrations'] = data['registrations']
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
        key=lambda x: (x[1]['registrations'], x[1]['alive'], -x[1]['users']),
        reverse=True)
    return render_template('index.html', statuses=sorted_statuses)


update_status(force=True)
asgi = WsgiToAsgi(app)
