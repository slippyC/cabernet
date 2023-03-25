"""
MIT License

Copyright (C) 2023 ROCKY4546
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

import logging

import lib.common.utils as utils
import lib.common.exceptions as exceptions

from lib.common.decorators import getrequest
from lib.common.decorators import postrequest
from lib.web.pages.templates import web_templates
from lib.db.db_plugins import DBPlugins
from lib.plugins.plugin_manager.plugin_manager import PluginManager

@getrequest.route('/api/pluginsform')
def get_plugins_form_html(_webserver, _namespace=None, _sort_col=None, _sort_dir=None, filter_dict=None):
    plugins_form = PluginsFormHTML(_webserver.config)

    _area = _webserver.query_data.get('area')
    _plugin = _webserver.query_data.get('plugin')
    _repo = _webserver.query_data.get('repo')
    
    if _area is None and _plugin is None and _repo is None:
        _webserver.do_mime_response(
            404, 'text/html', web_templates['htmlError']
            .format('404 - Badly formed request'))
    elif _area:
            try:
                form = plugins_form.get(_area)
                _webserver.do_mime_response(200, 'text/html', form)
            except exceptions.CabernetException as ex:
                _webserver.do_mime_response(
                    404, 'text/html', web_templates['htmlError']
                    .format('404 - Badly formed area request'))
    elif _plugin and _repo:
        try:
            form = plugins_form.get_plugin(_repo, _plugin)
            _webserver.do_mime_response(200, 'text/html', form)
        except exceptions.CabernetException as ex:
            _webserver.do_mime_response(
                404, 'text/html', web_templates['htmlError']
                .format('404 - Badly formed plugin request'))
    else:
        # case where plugin and repo are not provided together
        _webserver.do_mime_response(
            404, 'text/html', web_templates['htmlError']
            .format('404 - Badly formed plugin/repo request'))
        



@postrequest.route('/api/pluginsform')
def post_plugins_html(_webserver):
    action = _webserver.query_data.get('action')
    pluginid = _webserver.query_data.get('pluginId')
    repoid = _webserver.query_data.get('repoId')
    if action and pluginid and repoid:
        action = action[0]
        pluginid = pluginid[0]
        repoid = repoid[0]
        if action == "deletePlugin":
            pm = PluginManager(_webserver.config, _webserver.plugins)
            results = pm.delete_plugin(repoid, pluginid, _webserver.sched_queue)
            _webserver.do_mime_response(200, 'text/html', 'STATUS: Deleting plugin: {}:{}<br> '.format(repoid, pluginid) + str(results))
        elif action == "installPlugin":
            pm = PluginManager(_webserver.config, _webserver.plugins)
            results = pm.install_plugin(repoid, pluginid, _webserver.sched_queue)
            _webserver.do_mime_response(200, 'text/html', 'STATUS: Installing plugin: {}:{}<br> '.format(repoid, pluginid) + str(results))
        else:
            _webserver.do_mime_response(200, 'text/html', "doing something else"+str(action[0]))
        
    else:
        _webserver.do_mime_response(
            404, 'text/html', web_templates['htmlError']
            .format('404 - Badly formed request'))

       

class PluginsFormHTML:

    def __init__(self, _config):
        self.logger = logging.getLogger(__name__)
        self.config = _config
        self.plugin_db = DBPlugins(self.config)
        self.active_tab_name = None
        self.num_of_plugins = 0
        self.plugin_data = None
        self.area = None

    def get(self, _area):
        self.area = _area
        return ''.join([self.header, self.body])

    def get_plugin(self, _repo_id, _plugin_id):
        plugin_defn = self.plugin_db.get_plugins(
                _installed=None,
                _repo_id=_repo_id,
                _plugin_id=_plugin_id)
        if not plugin_defn:
            self.logger.warning(
                'HTTP request: Unknown plugin: {}'
                .format(_plugin_id))
            raise exceptions.CabernetException(
                'Unknown Plugin: {}'
                .format(_plugin_id))
        plugin_defn = plugin_defn[0]
        return ''.join([self.get_plugin_header(plugin_defn), self.get_menu_section(plugin_defn), self.get_plugin_section(plugin_defn)])

    def get_menu_section(self, _plugin_defn):
        pluginid = _plugin_defn['id']
        repoid = _plugin_defn['repoid']
        return ''.join([
            '<div id="menuActionStatus"></div>',
            '<form id="menuForm" action="/api/pluginsform" method="post">'
            '<input type="hidden" name="action" value="">',
            '<input type="hidden" name="pluginId" value="',
            pluginid, '">',
            '<input type="hidden" name="repoId" value="',
            repoid, '">',
            '<div id="pluginActions" class="menuCanvas listItemHide">',
            '<div class="menuPanel">',
            '<ul class="menuList">',
            '<li class="menuItem">',
            '<button type="submit" name="action" value="deletePlugin" class="menuButton" ',
            'title="Deletes the plugin folder and scheduled events">',
            '<i class="md-icon" style="padding-right: 5px; font-size: 1.7em;">delete</i>',
            'Delete Plugin only',
            '</button>',
            '</li>',

            '<li class="menuItem">',
            '<button type="submit" formtarget="#menuActionStatus" name="action" value="deletePlugin2" class="menuButton">',
            '<i class="md-icon" style="padding-right: 5px; font-size: 1.7em;">delete</i>',
            'Delete Plugin and Data',
            '</button>',
            '</li>',

            '</ul>',
            '<ul class="menuList">',

            '<li class="menuItem">',
            '<button type="submit" name="action" value="installPlugin" class="menuButton" ',
            'title="Download and install latest version of plugin, updates handler and schedule events">',
            '<i class="md-icon" style="padding-right: 5px; font-size: 1.7em;">download</i>',
            'Install Plugin',
            '</button>',
            '</li>',

            '<li class="menuItem">',
            '<button type="submit" name="action" value="upgradePlugin" class="menuButton">',
            '<i class="md-icon" style="padding-right: 5px; font-size: 1.7em;">upgrade</i>',
            'Upgrade Plugin',
            '</button>',
            '</li>',

            '<li class="menuItem">',
            '<button type="submit" name="action" value="createInstance" class="menuButton">',
            '<i class="md-icon" style="padding-right: 5px; font-size: 1.7em;">add_circle</i>',
            'Create Instance',
            '</button>',
            '</li>',

            '<li class="menuItem">',
            '<button type="submit" name="action" value="deleteInstance" class="menuButton">',
            '<i class="md-icon" style="padding-right: 5px; font-size: 1.7em;">delete</i>',
            'Delete Instance',
            '</button>',
            '</li>',

            '</ul>',
            '</div>',
            '</div></form>'])

    
    def get_plugin_header(self, _plugin_defn):
        instances = self.plugin_db.get_instances(_namespace=_plugin_defn['name'])
        if instances:
            # array of instance names
            instances = instances[_plugin_defn['name']]
        else:
            instances = None
        
        if not _plugin_defn['version'].get('latest'):
            _plugin_defn['version']['latest'] = None

        latest_version = _plugin_defn['version']['latest']
        upgrade_available = ''
        if latest_version != _plugin_defn['version']['current']:
            upgrade_available = '<button class="menuIconButton" type="button" style="margin-left:10px;">Upgrade to {}</button>' \
                .format(latest_version)

        html = ''.join([
            '<div><div style="display: flex;"><div class="pluginIcon">',
            '<a href="#" onclick=\'display_plugins()\'>',
            '<div ><i class="md-icon">arrow_back</i></div></a></div>',
            '<div class="pluginSectionName">',
            str(_plugin_defn['name']), '</div></div>',

            '<div>', str(_plugin_defn['summary']), '</div>',

            '<div style="position: relative;">',
            '<img class="image-size" src="/api/manifest?plugin=',
                _plugin_defn['name'], '&key=icon" alt="',
                _plugin_defn['name'],'">',
            '</div>',

            '<div>',
            str(_plugin_defn['description']),
            '</div>',
            '<div style="background: var(--docked-drawer-background);">'
        ])
        return html
    
    def get_plugin_section(self, _plugin_defn):
        pluginid = _plugin_defn['id']
        repoid = _plugin_defn['repoid']

        instances = self.plugin_db.get_instances(_namespace=_plugin_defn['name'])
        if instances:
            # array of instance names
            instances = instances[_plugin_defn['name']]
        else:
            instances = None
        
        if not _plugin_defn['version'].get('latest'):
            _plugin_defn['version']['latest'] = None

        latest_version = _plugin_defn['version']['latest']
        upgrade_available = ''
        if latest_version != _plugin_defn['version']['current']:
            upgrade_available = '<button class="menuIconButton" type="button" style="margin-left:10px;">Upgrade to {}</button>' \
                .format(latest_version)


        html = ''.join([
            '<button class="menuIconButton menuSection" type="button" onclick="show_menu(this, \'pluginActions\');">',
            '<i class="md-icon" STYLE="font-size: 1.7em;">menu</i>',
            '</button>',

            '<div class="pluginSection">',
            '<div class="pluginSectionName">Dependencies: </div>',
            '<div class="pluginValue">',
            str(_plugin_defn['dependencies']), 
            '</div>',
            '</div>',

            '<div class="pluginSection">',
            '<div class="pluginSectionName">Version Installed: </div>',
            '<div style="float:left; margin-top:3px;" class="pluginValue">',
            str(_plugin_defn['version']['current']), '</div>',
            upgrade_available,
            '</div>',

            '<div class="pluginSection">',
            '<div class="pluginSectionName">Latest Version: </div>',
            '<div class="pluginValue">',
            str(_plugin_defn['version']['latest']),
            '</div>',
            '</div>',

            '<div class="pluginSection">',
            '<div class="pluginSectionName">Source: </div>',
            '<div class="pluginValue">',
            str(_plugin_defn['source']),
            '</div>',
            '</div>',

            '<div class="pluginSection">',
            '<div class="pluginSectionName">License: </div>',
            '<div class="pluginValue">',
            str(_plugin_defn['license']),
            '</div>',
            '</div>',

            '<div class="pluginSection">',
            '<div class="pluginSectionName">Author: </div>',
            '<div class="pluginValue">',
            str(_plugin_defn['provider-name']),
            '</div>',
            '</div>',

            '<div class="pluginSection">',
            '<div class="pluginSectionName">Origin: </div>',
            '<div class="pluginValue">',
            'Cabernet Plugin Repository',
            '</div>',
            '</div>',

            '<div class="pluginSection">',
            '<div class="pluginSectionName">Size: </div>',
            '<div class="pluginValue">',
            '256kB',
            '</div>',
            '</div>',

            '<div class="pluginSection">',
            '<div class="pluginSectionName">Category: </div>',
            '<div class="pluginValue">',
            str(_plugin_defn['category']),
            '</div>',
            '</div>',

            '<div class="pluginSection">',
            '<div class="pluginSectionName">Related Website: </div>',
            '<div class="pluginValue">',
            str(_plugin_defn['website']),
            '</div>',
            '</div>',

            '<div class="pluginSection">',
            '<div class="pluginSectionName">Instances: </div>',
            '<div class="pluginValue">',
            str(instances),
            '</div>',
            '</div>',

            '</div>',

            '<div class="pluginSection">',
            '<div class="pluginSectionName">Processing Stuff: </div>',
            '<div class="pluginValue">',
            'delete instance, install plugin, delete plugin, add instance, ',
            ' upgrade plugin, install specific version of plugin',
            '</div>',
            '</div>',

            '<div class="pluginSection">',
            '<div class="pluginSectionName">Add Instance',
            '<button class="pluginIconButton" onclick=\'load_task_url(',
            '"/api/schedulehtml?task=', '&trigger=1");return false;\'>',
            '<i class="pluginIcon md-icon" style="padding-left: 1px; text-align: left;">add</i></button>',
            '</div>',
            '</div>',
            '</div>'
        ])
        return html

    def form_plugins(self, _is_installed):
        plugin_defns = self.plugin_db.get_plugins(
            _is_installed, None, None)

        self.logger.warning(plugin_defns)

        plugins_list = ''
        for plugin_defn in sorted(plugin_defns, key=lambda p: p['id']):
            repo_id = plugin_defn['repoid']
            plugin_id = plugin_defn['id']
            plugin_name = plugin_defn['name']

            img_size = self.lookup_config_size()
            if not plugin_defn['external']:
                location = ' (Internal)'
            else:
                location = ''

            latest_version = plugin_defn['version']['latest']
            upgrade_available = ''
            if _is_installed:
                if latest_version != plugin_defn['version']['current']:
                    upgrade_available = '<div class="bottom-left">Upgrade to {}</div>' \
                        .format(latest_version)
                current_version = plugin_defn['version']['current']
            else:
                current_version = ''
            

            self.logger.warning('{} {} {} {} {} {} {}'.format(plugin_id, repo_id, plugin_name, img_size, upgrade_available, location, plugin_defn['version']['current']))

            plugins_list += ''.join([
                '<button class="plugin_item" type="button"',
                ' onclick=\'load_plugin_url("/api/pluginsform?',
                'plugin=', plugin_id, 
                '&repo=', repo_id,
                '")\'>',
                '<div>',
                '<div style="position: relative;">',
                '<img src="/api/manifest?plugin=',
                plugin_name, '&key=icon" width="', str(img_size), '" alt="',
                plugin_name,'">',
                upgrade_available,
                
                '</div><div>', plugin_name, location,
                '</div><div class="pluginText-secondary">',
                str(current_version), '</div></div>',
                '</button>'
                ])
        return plugins_list

    @property
    def header(self):
        return ''.join([
            '<html><head>',
            '</head>'
        ])

    @property
    def form(self):
        if self.area == 'My_Plugins':
            forms_html = ''.join([
                '<div class="plugin_list">',
                self.form_plugins(True), '</div>'])
        elif self.area == 'Catalog':
            forms_html = ''.join([
                '<div class="plugin_list">',
                self.form_plugins(_is_installed=False), 
                '</div>'])
        else:
            self.logger.warning('HTTP request: unknown area: {}'.format(self.area))
            raise exceptions.CabernetException('Unknown Tab: {}'.format(self.area))
        return forms_html

    @property
    def body(self):
        return ''.join([
            '<body>', self.form, '</body>'])

    def lookup_config_size(self):
        size_text = self.config['channels']['thumbnail_size']
        if size_text == 'None':
            return 0
        elif size_text == 'Tiny(16)':
            return 16
        elif size_text == 'Small(48)':
            return 48
        elif size_text == 'Medium(128)':
            return 128
        elif size_text == 'Large(180)':
            return 180
        elif size_text == 'X-Large(270)':
            return 270
        elif size_text == 'Full-Size':
            return None
        else:
            return None
