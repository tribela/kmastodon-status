import datetime

import httpx
from multiprocessing.pool import ThreadPool
from packaging import version

from flask import Flask, render_template
from asgiref.wsgi import WsgiToAsgi

app = Flask(__name__)

instances = {
    'qdon.space',
    'planet.moe',
    'twingyeo.kr',
    'kurry.social',
    'jmm.kr',
    'ani.work',
    'occm.cc',
    'parfait.day',
    'furpark.kr',
    'uri.life',
    'duk.space',
    'maratang.life',
    'mastodon.mnetwork.co.kr',
    'bakedbean.xyz',
    'renkontu.com',
    'mustard.blog',
    'social.silicon.moe',
    'toot.funami.tech',
    't.chadole.com',
    'mastodon.simpreative.network',
}

statuses = {
    instance: {
        'name': '',
        'software': '',
        'version': '',
        'alive': False,
        'logins': 0,
        'registrations': 0,
        'statuses': 0,
        'open_registrations': False,
        'approval_required': False,
    }
    for instance in instances
}

last_updated = datetime.datetime.now()


def get_software(instance: str) -> tuple[str, str]:
    try:
        data = httpx.get(f'https://{instance}/.well-known/nodeinfo').json()
        nodeinfo_url = data['links'][0]['href']

        nodeinfo = httpx.get(nodeinfo_url).json()

        return (nodeinfo['software']['name'], nodeinfo['software']['version'])
    except httpx.HTTPError:
        return None
    except Exception:
        return None


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
        software, version = get_software(instance)
        statuses[instance]['software'] = software
        statuses[instance]['version'] = version
        statuses[instance]['alive'] = True

        data = httpx.get(f'https://{instance}/api/v1/instance').json()

        statuses[instance]['name'] = data['title']
        statuses[instance]['open_registrations'] = data['registrations']
        statuses[instance]['approval_required'] = data['approval_required']

        statistics = httpx.get(f'https://{instance}/api/v1/instance/activity').json()[1]

        statuses[instance]['logins'] = int(statistics['logins'])
        statuses[instance]['registrations'] = int(statistics['registrations'])
        statuses[instance]['statuses'] = int(statistics['statuses'])

    except httpx.HTTPError:
        statuses[instance]['alive'] = False
    except Exception:
        statuses[instance]['alive'] = False


def parse_version(ver: str) -> version.Version:
    # Get rid of postfixes
    ver = ver.split('+')[0]
    try:
        return version.parse(ver)
    except ValueError:
        return (0, 0, 0)


@app.route('/')
def index():
    update_status()
    # render statuses with template

    sorted_statuses = sorted(
        statuses.items(),
        key=lambda x: (
            x[1]['alive'],
            x[1]['logins'],
            x[1]['statuses'],
            x[1]['registrations'],
            parse_version(x[1]['version']),
            x[1]['open_registrations'],
            not x[1]['approval_required'],
        ),
        reverse=True)
    return render_template('index.html', statuses=sorted_statuses)


update_status(force=True)
asgi = WsgiToAsgi(app)
