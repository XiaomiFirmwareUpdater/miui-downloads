#!/usr/bin/env python3.7
"""Xiaomi MIUI Downloads scraper"""

import json
from datetime import datetime
from glob import glob
from os import remove, system, environ
import requests

STABLE = []
WEEKLY = []
DEVICES = {}
with open('names.json', 'r') as devices_json:
    NAMES = json.load(devices_json)


def fetch_devices():
    """
    fetch MIUI downloads devices
    """
    headers = {
        'pragma': 'no-cache',
        'accept-encoding': 'gzip, deflate, br',
        'accept-language': 'en-US,en;q=0.9',
        'accept': 'application/json, text/javascript, */*; q=0.01',
        'cache-control': 'no-cache',
        'authority': 'c.mi.com',
        'x-requested-with': 'XMLHttpRequest',
        'referer': 'https://c.mi.com/oc/miuidownload/',
    }

    url = 'http://c.mi.com/oc/rom/getphonelist'
    data = requests.get(url, headers=headers).json()['data']['phone_data']['phone_list']
    ids = [i['id'] for i in data]
    return ids


def fetch_roms(device_id, url):
    """
    fetch MIUI ROMs downloads
    """
    headers = {
        'Pragma': 'no-cache',
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Referer': f'http://c.mi.com/oc/miuidownload/detail?device={device_id}',
        'X-Requested-With': 'XMLHttpRequest',
        'Connection': 'keep-alive',
        'Cache-Control': 'no-cache',
    }
    data = requests.get(
        url, headers=headers, verify=False).json()['data']['device_data']['device_list']
    if not data:
        return
    for device, info in data.items():
        roms = []
        try:
            if info['stable_rom']['rom_url']:
                roms.append({'id': device_id, 'name': device,
                             'size': info['stable_rom']['size'],
                             'download': info['stable_rom']['rom_url']})
        except KeyError:
            pass
        try:
            if info['developer_rom']['rom_url']:
                roms.append({'id': device_id, 'name': device,
                             'size': info['developer_rom']['size'],
                             'download': info['developer_rom']['rom_url']})
        except KeyError:
            pass
        for rom in roms:
            file = rom['download'].split('/')[-1]
            if file.endswith('.tgz'):
                if file.split('_images_')[1].split('_')[0].startswith('V'):
                    STABLE.append(rom)
                else:
                    WEEKLY.append(rom)
            else:
                if file.split('_')[2].startswith('V'):
                    STABLE.append(rom)
                else:
                    WEEKLY.append(rom)


def gen_json(data, folder):
    """
    generate json file with device's info for each rom link
    :param data: a list of dicts
    :param folder: stable/weekly
    """
    for item in data:
        device_id = item['id']
        name = item['name']
        size = item['size']
        rom = item['download']
        file = rom.split('/')[-1]
        model = ''
        if file.endswith('.tgz'):
            codename = file.split('_images')[0]
            version = rom.split('/')[-2]
            android = file.split('_')[-2]
        else:
            try:
                model = file.split('_')[1]
                version = file.split('_')[2]
                android = file.split('_')[-1].split('.zip')[0]
            except IndexError as err:
                print(item, err)
                continue
            try:
                codename = [i for i, j in NAMES.items() if j['model'] == model][0]
            except IndexError as err:
                print(item)
                print(f"can't find codename for {model}\n{err}")
                continue
        with open(f'{folder}/{codename}.json', 'w') as output:
            output.writelines(' {' + '\n' + '  "android": "' + android + '",' + '\n')
            output.writelines('  "codename": "' + codename + '",' + '\n')
            output.writelines('  "device": "' + name + '",' + '\n')
            output.writelines('  "download": "' + rom + '",' + '\n')
            output.writelines('  "filename": "' + file + '",' + '\n')
            output.writelines('  "version": "' + version + '",' + '\n')
            output.writelines('  "size": "' + size + '"' + '\n' + ' }')
        if not model:
            model = codename.split('_')[0]
        DEVICES.update({codename: {
            'name': name,
            'model': model,
            'id': device_id
        }})


def merge_json(name):
    """
    merge all devices json files into one file
    :param name: folder stable/weekly
    """
    print(f"Creating {name} JSON")
    json_files = [x for x in sorted(glob(f'{name}/*.json')) if 'stable.json' not in x
                  and 'weekly.json' not in x]
    json_data = []
    for file in json_files:
        with open(file, "r") as json_file:
            json_data.append(json.load(json_file))
    with open(f'{name}/{name}.json', "w") as output:
        json.dump(json_data, output, indent=1)
    for file in json_files:
        remove(file)


def git_commit_push():
    """
    git add - git commit - git push
=    """
    today = str(datetime.today()).split('.')[0]
    system("git add */*.json && "
           "git -c \"user.name=XiaomiFirmwareUpdater\" -c "
           "\"user.email=xiaomifirmwareupdater@gmail.com\" "
           "commit -m \"[skip ci] sync: {}\" && "" \
           ""git push -q https://{}@github.com/XiaomiFirmwareUpdater/"
           "miui-downloads.git HEAD:global"
           .format(today, environ['XFU']))


def main():
    """
    Main scraping script
    """
    devices_ids = fetch_devices()
    for device_id in devices_ids:
        url = f'http://c.mi.com/oc/rom/getdevicelist?phone_id={device_id}'
        fetch_roms(device_id, url)
    data = {'stable': STABLE, 'weekly': WEEKLY}
    for name, details in data.items():
        gen_json(details, name)
        merge_json(name)

    with open('names.json', 'w') as out_json:
        json.dump(dict(sorted(DEVICES.items())), out_json, indent=1)
    git_commit_push()
    print('Done')


if __name__ == '__main__':
    main()
