#!/usr/bin/env python3.7
"""Xiaomi MIUI Downloads scraper"""

import json
from collections import OrderedDict
from datetime import datetime
from glob import glob
from os import remove, system, environ
import requests
from bs4 import BeautifulSoup

STABLE = []
WEEKLY = []

with open('devices.json', 'r') as devices_json:
    DEVICES = json.load(devices_json)


def fetch(codename, pid):
    """
    fetch zip roms from MIUI downloads website
    :param codename: Xiaomi device codename
    :param pid: device pid on downloads site
    :return: roms - a list of links
    """
    url = f'http://en.miui.com/download-{pid}.html'

    if '_' not in codename:  # switch to china website if codename has no region
        url = url.replace('en.', '')
    try:
        response = requests.get(url)
    except requests.exceptions.ConnectionError:
        print(f'something is wrong with url {url}')
        roms = []
        return roms
    page = BeautifulSoup(response.content, 'html.parser')
    roms = [link['href'] for link in page.find_all('a') if '.zip' in str(link)]
    roms = list(OrderedDict.fromkeys(roms))
    return roms


def gen_json(links, folder):
    """
    generate json file with device's info for each rom link
    :param links: a list of links
    :param folder: stable/weekly
    """
    for rom in links:
        file = rom.split('/')[-1]
        model = file.split('_')[1]
        version = file.split('_')[2]
        android = file.split('_')[-1].split('.zip')[0]
        try:
            codename = [i for i, j in DEVICES.items() if j['model'] == model][0]
        except IndexError as err:
            print(f"can't find codename for {model}\n{err}")
            continue
        name = DEVICES[codename]['name']
        with open(f'{folder}/{codename}.json', 'w') as output:
            output.writelines(' {' + '\n' + '  "android": "' + android + '",' + '\n')
            output.writelines('  "codename": "' + codename + '",' + '\n')
            output.writelines('  "device": "' + name + '",' + '\n')
            output.writelines('  "download": "' + rom + '",' + '\n')
            output.writelines('  "filename": "' + file + '",' + '\n')
            output.writelines('  "version": "' + version + '"' + '\n' + ' }')


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
           "miui-downloads.git HEAD:master"
           .format(today, environ['XFU']))


def main():
    """
    Main scraping script
    """
    fetched = {}
    print('Fetching latest downloads')
    for codename, info in DEVICES.items():
        if not info['pid']:
            continue
        pid = info['pid']
        if 'China' in info['name']:
            site = 'cn'
        else:
            site = 'en'
        if {pid_: region for pid_, region in fetched.items() if pid == pid_ and site == region}:
            continue
        roms = fetch(codename, pid)
        if not roms:
            continue
        fetched.update({pid: site})
        for rom in roms:
            if str(rom.split('/')[-1].split('_')[2]).startswith('V'):
                STABLE.append(rom)
            else:
                WEEKLY.append(rom)
    data = {'stable': STABLE, 'weekly': WEEKLY}
    for name, details in data.items():
        gen_json(details, name)
        merge_json(name)
    git_commit_push()
    print('Done')


if __name__ == '__main__':
    main()
