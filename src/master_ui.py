#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Created on 2017-12-22
@author: foxty

UI for master node
"""
import logging
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify
from common import dump_json
from master import MasterDAO
logging.basicConfig(level=logging.INFO)


_APP = Flask(__name__,
             static_folder='../web/static/',
             static_url_path='/static',
             template_folder='../web/template/')
_DAO = MasterDAO()


@_APP.route("/")
def index():
    return render_template('index.html')


@_APP.route('/api/agents', methods=['GET'])
def get_agents():
    agents = _DAO.get_agents()
    return dump_json(agents)


@_APP.route('/api/agents/<aid>/report/system', methods=['GET'])
def get_agent_sysreports(aid):
    end = datetime.now()
    start = end - timedelta(hours=1)
    reports = _DAO.get_sysreports(aid, start, end)
    return dump_json(reports)


@_APP.route('/api/agents/<aid>/report/cpu', methods=['GET'])
def get_agent_cpureports(aid):
    end = datetime.now()
    start = end - timedelta(hours=1)
    reports = _DAO.get_cpureports(aid, start, end)
    return dump_json(reports)


@_APP.route('/api/agents/<aid>/report/memory', methods=['GET'])
def get_agent_memreports(aid):
    end = datetime.now()
    start = end - timedelta(hours=1)
    reports = _DAO.get_memreports(aid, start, end)
    return dump_json(reports)


def ui_main(host='0.0.0.0', port=8080, debug=False):
    logging.info('starting master ui...')
    _APP.jinja_env.variable_start_string = '{-'
    _APP.jinja_env.variable_end_string = '-}'
    _APP.jinja_env.auto_reload = True
    _APP.config['TEMPLATES_AUTO_RELOAD'] = True
    _APP.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    ui_main(port=8081, debug=True)