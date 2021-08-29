"""
MIT License

Copyright (C) 2021 ROCKY4546
https://github.com/rocky4546

This file is part of Cabernet

Permission is hereby granted, free of charge, to any person obtaining a copy of this software
and associated documentation files (the "Software"), to deal in the Software without restriction,
including without limitation the rights to use, copy, modify, merge, publish, distribute,
sublicense, and/or sell copies of the Software, and to permit persons to whom the Software
is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or
substantial portions of the Software.
"""

import importlib
import json
import logging
import pathlib
import re
import time
import urllib.request
from threading import Thread

import lib.common.utils as utils
from lib.db.db_scheduler import DBScheduler
from lib.db.db_plugins import DBPlugins
from lib.common.decorators import handle_url_except
from lib.common.decorators import handle_json_except
from lib.common.decorators import getrequest
from lib.web.pages.templates import web_templates
from lib.updater.cabernet import CabernetUpgrade
import lib.updater.cabernet as cabernet

STATUS = ''
IS_UPGRADING = False


@getrequest.route('/api/upgrade')
def upgrade(_webserver):
    global STATUS
    global IS_UPGRADING
    v = Updater(_webserver.plugins)
    try:
        if 'id' in _webserver.query_data:
            if _webserver.query_data['id'] != utils.CABERNET_NAMESPACE:
                _webserver.do_mime_response(501, 'text/html', 
                    web_templates['htmlError'].format('501 - Invalid ID'))
                return
            if not IS_UPGRADING:
                IS_UPGRADING = True
                v.sched_queue = _webserver.sched_queue
                STATUS = ''
                cabernet.STATUS = ''
                t = Thread(target=v.upgrade_app, args=(_webserver.query_data['id'],))
                t.start()
            _webserver.do_mime_response(200, 'text/html', ''.join([cabernet.STATUS, STATUS]))
            return
        else:
            _webserver.do_mime_response(501, 'text/html',
                web_templates['htmlError'].format('404 - Unknown action'))
    except KeyError:
        _webserver.do_mime_response(501, 'text/html', 
            web_templates['htmlError'].format('501 - Badly formed request'))


def check_for_updates(plugins):
    v = Updater(plugins)
    v.update_version_info()


class Updater:

    def __init__(self, _plugins):
        self.logger = logging.getLogger(__name__)
        self.version_re = re.compile(r'(\d+\.\d+)\.\d+')
        self.plugins = _plugins
        self.config_obj = _plugins.config_obj
        self.config = _plugins.config_obj.data
        self.plugin_db = DBPlugins(self.config)
        self.sched_queue = None

    def scheduler_tasks(self):
        scheduler_db = DBScheduler(self.config)
        if scheduler_db.save_task(
                'Applications',
                'Check for Updates',
                'internal',
                None,
                'lib.updater.updater.check_for_updates',
                20,
                'thread',
                'Checks cabernet and all plugins for updated versions'
                ):
            scheduler_db.save_trigger(
                'Applications',
                'Check for Updates',
                'interval',
                interval=2850,
                randdur=60
                )
            scheduler_db.save_trigger(
                'Applications',
                'Check for Updates',
                'startup')

    def update_version_info(self):
        c = CabernetUpgrade(self.plugins)
        c.update_version_info()

    def import_manifest(self):
        """
        Loads the manifest for cabernet from a file
        """
        json_settings = importlib.resources.read_text(self.config['paths']['resources_pkg'], MANIFEST_FILE)
        settings = json.loads(json_settings)
        return settings

    def load_manifest(self, _manifest):
        """
        Loads the cabernet manifest from DB
        """
        return self.plugin_db.get_plugins(_manifest)[0]

    def save_manifest(self, _manifest):
        """
        Saves to DB the manifest for cabernet
        """
        self.plugin_db.save_plugin(_manifest)
 
    @handle_json_except 
    @handle_url_except 
    def github_releases(self):
        json_releases = importlib.resources.read_text(self.config['paths']['resources_pkg'], 'github_releases.json')
        releases = json.loads(json_releases)
        return releases

        url = ''.join([
            self.manifest['github_repo'], '/releases'
            ])
        login_headers = {'Content-Type': 'application/json', 'User-agent': utils.DEFAULT_USER_AGENT}
        release_req = urllib.request.Request(url, headers=login_headers)
        with urllib.request.urlopen(release_req) as resp:
            release_list = json.load(resp)
        return release_list

    def get_next_release(self, release_data_list):
        current_version = self.config['main']['version']
        x = self.version_re.match(current_version)
        c_version_float = float(re.findall(r'(\d+\.\d+)\.\d+', current_version)[0])
        prev_version = release_data_list[0]['tag_name']
        for data in release_data_list:
            version_float = float(re.findall(r'(\d+\.\d+)\.\d+', data['tag_name'])[0])
            if version_float <= c_version_float:
                break
            prev_version = data['tag_name']
        return prev_version

    def upgrade_app(self, _id):
        """
        Initial request to perform an upgrade
        """
        global STATUS
        global IS_UPGRADING

        app = CabernetUpgrade(self.plugins)
        if not app.upgrade_app():
            STATUS += '<script type="text/javascript">upgrading = "failed"</script>'
            time.sleep(1)
            IS_UPGRADING = False
            return

        # what do we do with plugins?  They go here if necessary
        STATUS += '(TBD) Upgrading plugins...<br>\r\n'

        STATUS += 'Restarting app in 3...<br>\r\n'
        time.sleep(0.8)
        STATUS += '2...<br>\r\n'
        time.sleep(0.8)
        STATUS += '1...<br>\r\n'
        STATUS += '<script type="text/javascript">upgrading = "success"</script>'
        time.sleep(1)
        IS_UPGRADING = False
        self.restart_app()
        
        
    def restart_app(self):
        # get schedDB and find restart taskid.
        scheduler_db = DBScheduler(self.config)
        task = scheduler_db.get_tasks('Applications', 'Restart')[0]
        self.sched_queue.put({'cmd': 'runtask', 'taskid': task['taskid'] })



    def download_zip(self, _zip_url):
        buf_size = 2 * 16 * 16 * 1024
        save_path = pathlib.Path(self.config['paths']['tmp_dir']).joinpath(utils.CABERNET_NAMESPACE + '.zip')
        h = {'Content-Type': 'application/zip', 'User-agent': utils.DEFAULT_USER_AGENT}
        req = urllib.request.Request(_zip_url, headers=h)
        with urllib.request.urlopen(req) as resp:
            with open(save_path, 'wb') as out_file:
                while True:
                    chunk = resp.read(buf_size)
                    if not chunk:
                        break
                    out_file.write(chunk)
