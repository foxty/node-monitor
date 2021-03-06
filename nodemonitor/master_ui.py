#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Created on 2017-12-22
@author: foxty

UI for master node
"""
import sys, os
import logging
import socket
from datetime import datetime, timedelta
from flask import Flask, request, render_template
from common import YAMLConfig, dump_json, set_logging
from model import TSDAgg, Agent, NSystemReport, NCPUReport, NMemoryReport, NDiskReport, \
    SInfo, SInfoHistory, SPidstatReport, SJstatGCReport, init_db
from master_cli import NodeConnector


_CONFIG = None
_APP = Flask(__name__,
             static_folder='../web/dist/',
             static_url_path='',
             template_folder='../web/dist/')


def calc_daterange(req):
    start_at = int(req.args.get('start_at'))
    end_at = int(req.args.get('end_at'))
    start = datetime.utcfromtimestamp(start_at/1000)
    end = datetime.utcfromtimestamp(end_at/1000)
    return start, end


_SAMPLE_INTERVAL = [120, 300, 600, 900, 1800, 3600, 2*3600, 6*3600, 12*3600, 24*3600]


def calc_downsample(start, end, agg, samples=60):
    """
    Calculate downsample for ts series
    :param start: in seconds
    :param end: in seconds
    :param agg: aggregation algo for down sample
    :param samples:
    :return:
    """
    expect_interval = (end - start)/samples
    candidate_intervals = filter(lambda x: x < expect_interval, _SAMPLE_INTERVAL)
    interval = candidate_intervals[-1] if len(candidate_intervals) > 0 else None
    return '%ds-%s' % (interval, agg.value) if interval is not None else None


@_APP.errorhandler(Exception)
def exception_handler(error):
    logging.exception('unexpected error occurs')
    return dump_json({'code': 400, 'message': error.message}), 400, {'Content-Type': 'application/json'}


@_APP.route("/")
def index():
    return render_template('index.html')


@_APP.route('/api/dashboard/summary')
def dashboard_summary():
    summary = {'agent_count': Agent.count(),
               'service_count': SInfo.count(),
               'alarm_count': 0,
               'sample_count': 0}
    return dump_json(summary)


@_APP.route('/api/agents/by_load1')
def get_agents_byload1():
    agents = Agent.query_by_load1()
    return dump_json(agents)


@_APP.route('/api/agents', methods=['GET'])
def get_agents():
    mhost = os.getenv('MASTER_HOST', None) or socket.gethostname()
    mport = _CONFIG['master']['server']['port']
    master_addr = '%s:%s' % (mhost, mport)
    agents = Agent.query(orderby='last_msg_at DESC')
    thresh = datetime.utcnow() - timedelta(minutes=5)
    for a in agents:
        a.status = 'active' if a.last_msg_at and a.last_msg_at >= thresh else 'inactive'
    return dump_json({'agents': agents, 'master_addr': master_addr})


@_APP.route('/api/agents', methods=['POST'])
def add_agent():
    data = request.get_json()
    logging.info('request add agent: %s', data)
    nhost = data.get('host')
    mhost = data.get('master_addr')
    connectType = data.get('connect_type')
    u = data.get('username')
    p = data.get('password')
    logging.info('install agent on %s@%s with master=%s', u, nhost, mhost)
    basepath = os.path.dirname(sys.path[0])
    with NodeConnector(nhost, u, p) as nc:
        nc.install_agent(basepath, mhost)
    logging.info('agent installed on %s@%s finished.', u, nhost)
    return 'ok'


@_APP.route('/api/agents/<string:aid>', methods=['GET'])
def get_agent(aid):
    agent = Agent.get_by_id(aid)
    return dump_json(agent)


@_APP.route('/api/agents/<string:aid>', methods=['DELETE'])
def del_agent(aid):
    connectType = request.args.get('connect_type')
    u = request.args.get('username')
    p = request.args.get('password')
    agent = Agent.get_by_id(aid)
    logging.info('remove agent on %s@%s', u, agent)
    with NodeConnector(agent.host, u, p) as nc:
        nc.remove_agent()
        agent.remove()
    logging.info('agent removed on %s@%s finished.', u, agent)
    return dump_json(agent)


@_APP.route('/api/agents/<aid>/report/system', methods=['GET'])
def get_agent_sysreports(aid):
    reports = NSystemReport.query_by_rtime(aid, *calc_daterange(request))
    return dump_json(reports)


@_APP.route('/api/agents/<aid>/report/cpu', methods=['GET'])
def get_agent_cpureports(aid):
    reports = NCPUReport.query_by_rtime(aid, *calc_daterange(request))
    return dump_json(reports)


@_APP.route('/api/agents/<aid>/report/memory', methods=['GET'])
def get_agent_memreports(aid):
    reports = NMemoryReport.query_by_rtime(aid, *calc_daterange(request))
    return dump_json(reports)


@_APP.route('/api/agents/<aid>/report/disk', methods=['GET'])
def get_agent_diskreports(aid):
    reports = NDiskReport.query_by_rtime(aid, *calc_daterange(request))
    return dump_json(reports)


@_APP.route('/api/agents/<string:aid>/services')
def get_agent_services(aid):
    services = SInfo.query_by_aid(aid)
    status_map = {report.service_id: report for report in SPidstatReport.lst_report_by_aid(aid, len(services))}
    return dump_json({'services': services, 'services_status_map': status_map})


@_APP.route('/api/agents/<string:aid>/services/<string:service_id>')
def get_service_info(aid, service_id):
    service = SInfo.byid(service_id)
    start, end = calc_daterange(request)
    service_history = SInfoHistory.query_by_rtime(service_id, start, end)
    return dump_json({'service': service, 'service_history': service_history})


@_APP.route('/api/agents/<aid>/services/<service_id>/report/pidstat',
            methods=['GET'])
def get_service_pidstats(aid, service_id):
    reports = SPidstatReport.query_by_rtime(service_id, *calc_daterange(request))
    return dump_json(reports)


@_APP.route('/api/agents/<aid>/services/<service_id>/report/jstatgc',
            methods=['GET'])
def get_service_jstatgc(aid, service_id):
    start, end = calc_daterange(request)
    reports = SJstatGCReport.query_by_rtime(service_id, start, end)
    # shistory = SInfoHistory.query_by_rtime(service_id, start, end)
    # calculate gc stats and memory stats

    gcstat_recent, gcstat_range = None, None
    if reports:
        end_reps = []
        for i, rep in enumerate(reports):
            if i > 1 and rep.ts < reports[i-1].ts:
                end_reps.append(reports[i-1])
        end_reps.append(reports[-1])
        # 1st end reprot - start report to remove data beyond the range
        end_reps[0] = end_reps[0] - reports[0]

        range_rep = reduce(lambda acc, r: acc + r, end_reps)
        final_rep = reports[-1]
        gcstat_range = range_rep.to_gcstat('range')
        gcstat_recent = final_rep.to_gcstat('recent')
    return dump_json({'reports': reports, 'gcstats': [gcstat_range, gcstat_recent]})


def ui_main(config, debug=False):
    set_logging('ui.log')
    logging.info('starting manger ui...')
    dbcfg = config['master']['database']
    init_db(dbcfg)
    global _CONFIG
    _CONFIG = config
    _APP.jinja_env.variable_start_string = '{-'
    _APP.jinja_env.variable_end_string = '-}'
    _APP.jinja_env.auto_reload = True
    _APP.config['TEMPLATES_AUTO_RELOAD'] = True
    servercfg = config['ui']['server']
    _APP.run(host=servercfg['host'], port=servercfg['port'], debug=debug)


if __name__ == '__main__':
    basepath = os.path.dirname(sys.path[0])
    ui_main(YAMLConfig(os.path.join(basepath, 'conf', 'master.yaml')), debug=True)