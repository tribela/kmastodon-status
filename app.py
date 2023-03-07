import asyncio
import datetime
import math

import httpx

from asgiref.wsgi import WsgiToAsgi
from flask import Flask, render_template
from packaging import version


UPDATE_INTERVAL = 60 * 5

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
        'response_time': float('inf'),
        'logins': 0,
        'registrations': 0,
        'statuses': 0,
        'open_registrations': False,
        'approval_required': False,
        'score': 0,
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


async def update_status(force=False):
    global last_updated
    elapsed = (datetime.datetime.now() - last_updated).total_seconds()
    if elapsed < UPDATE_INTERVAL and force is False:
        return

    last_updated = datetime.datetime.now()

    await asyncio.gather(*[
        update_status_for_instance(instance)
        for instance in instances
    ])


async def update_status_for_instance(instance: str):
    global statuses

    try:
        async with httpx.AsyncClient() as client:
            [
                res_health,
                res_activity,
                res_instance,
            ] = await asyncio.gather(
                    *[client.get(url) for url in [
                        f'https://{instance}/health',
                        f'https://{instance}/api/v1/instance/activity',
                        f'https://{instance}/api/v1/instance',
                    ]]
                )

        if res_health.status_code != 200:
            statuses[instance]['alive'] = False
            return

        instance_data = res_instance.json()
        activity_data = res_activity.json()[1]

        statuses[instance]['software'] = 'mastodon'
        statuses[instance]['version'] = instance_data['version']
        statuses[instance]['alive'] = True

        statuses[instance]['name'] = instance_data['title']
        statuses[instance]['open_registrations'] = instance_data['registrations']
        statuses[instance]['approval_required'] = instance_data['approval_required']

        statuses[instance]['logins'] = int(activity_data['logins'])
        statuses[instance]['registrations'] = int(activity_data['registrations'])
        statuses[instance]['statuses'] = int(activity_data['statuses'])

        # Moving average
        if statuses[instance]['response_time'] == float('inf'):
            statuses[instance]['response_time'] = res_health.elapsed.total_seconds()
        else:
            statuses[instance]['response_time'] = (
                statuses[instance]['response_time'] * 0.5
                + res_health.elapsed.total_seconds() * 0.5
            )

    except httpx.HTTPError:
        statuses[instance]['alive'] = False

    statuses[instance]['score'] = score_function(statuses[instance])


def parse_version(ver: str) -> version.Version:
    # Get rid of postfixes
    ver = ver.split('+')[0]
    try:
        return version.parse(ver)
    except ValueError:
        version.Version('0.0.0')


def score_function(status):
    return (
        math.log2(status['logins'] + 1)
        + math.log2(status['statuses'] + 1)
        + math.log2(status['registrations'] + 1) * 0.1
        - math.log2(status['response_time']) * 0.5
    )


@app.route('/')
async def index():
    def sort_function(item):
        status = item[1]
        alive = status['alive']
        ver = parse_version(status['version'])
        open_registrations = status['open_registrations']
        approval_required = status['approval_required']
        score = status['score']

        return (
            alive,
            score,
            ver,
            open_registrations,
            not approval_required)

    sorted_statuses = sorted(
        statuses.items(),
        key=sort_function,
        reverse=True)
    return render_template('index.html', statuses=sorted_statuses)


async def worker():
    await update_status(force=True)
    while True:
        await asyncio.sleep(UPDATE_INTERVAL)
        await update_status()


asyncio.ensure_future(worker())
asgi = WsgiToAsgi(app)
