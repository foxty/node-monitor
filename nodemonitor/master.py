#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Created on 2017-12-22
@author: foxty

Node monitor master:
- Monitor node health (CPU, IO, Memory, Load)
- Monitor specified processes (CPU, IO, Memory, Pidstat and logs)
"""
# ==============================
#   Node Master
# ==============================
import os
import logging
import sys
import socket
import select
import SocketServer
import content_parser
import model
from datetime import datetime, timedelta
from threading import Timer
from uuid import uuid4
from common import YAMLConfig, Msg, InvalidMsgError, set_logging, read_agent_msg


class AlarmEngine(object):
    """manage alarms life cycle for agent & service
    Alarms:
        Node Alarm
            (CPU UTIL HIGH, CPU UTIL EXTREMELY HIGH)
            (DISK UTIL HIGH, DISK UTIL EXTREMELY HIGH)
            (LOAD1 HIGH, LOAD1 EXTREMELY HIGH)
            (LOAD5 HIGH, LOAD5 EXTREMELY HIGH)
            (LOAD15 HIGH, LOAD15 EXTREMELY HIGH)
            (SYS CS HIGH, SYS CS EXTREMELY HIGH)
            (MEMORY UTIL HIGH, MEMORY EXTREMELY HIGH)
        Service Alarm
            (CPU UTIL HIGH, CPU UTIL EXTREMELY HIGH)
            (MEMORY UTIL HIGH, MEMORY EXTREMELY HIGH)
    """

    def __init__(self):
        self._agent_status = {}
        self._live_alarms = []

    def process(self, report):
        """
        process event and reports
        :param report:
        :return:
        """
        pass

    def start(self):
        pass

    def stop(self):
        pass


# class AgentRequestHandler(SocketServer.StreamRequestHandler):
#     """All message are MonMsg and we should decode the msg here"""
#
#     def handle(self):
#         self.agentid = None
#         try:
#             self._loop()
#         except Exception as e:
#             logging.exception('error while processing data for %s', self.client_address)
#         finally:
#             if self.agentid:
#                 status = _MASTER.inactive_agent(self.agentid)
#                 logging.info('inactive agent %s ', status)
#             else:
#                 logging.info('agent from %s not registered, exit handler.', self.client_address)
#
#     def _chk_msg(self, msg):
#         if not _MASTER.find_agent(msg.agentid) and msg.msg_type != Msg.A_REG:
#             raise InvalidMsgError('agentid %s not registered from %s' % (msg.agentid, self.client_address))
#         elif not self.agentid:
#             self.agentid = msg.agentid
#             logging.info('new agent %s joined', self.client_address)
#         elif self.agentid != msg.agentid:
#             raise InvalidMsgError('agentid change detected %d->%d from %s'
#                                   % (self.agentid, msg.agentid, self.client_address))
#
#     def _recv_msg(self):
#         header = self.rfile.readline().strip().split(':')
#         if len(header) == 2 and 'MSG' == header[0] and header[1].isdigit():
#             data = self.rfile.read(int(header[1])).split('\n')
#             headers, body = data[:-1], data[-1]
#             msg = Msg.decode(headers, body)
#             msg.client_addr = self.client_address
#             logging.debug("recv msg type=%s,datalen=%s,size=%d from %s",
#                           msg.msg_type, header[1], len(data), self.client_address)
#             return msg
#         else:
#             raise InvalidMsgError('unsupported msg header %s from %s'%(header, self.client_address))
#
#     def _loop(self):
#         process = True
#         while process:
#             msg = self._recv_msg()
#             self._chk_msg(msg)
#             process = _MASTER.handle_msg(msg, self.client_address)
#             if not process:
#                 logging.info('msg handler stopped for %s from %s', msg, self.agentid)


class DataKeeper(object):

    def __init__(self, cfg):
        self._config = cfg
        self._interval = cfg['interval']
        self._policy = cfg['policy']
        self._count = 0
        self._run = False
        self._startat = None
        self._timer = None
        logging.info('data keeper created with interval=%d', self._interval)

    def start(self):
        self._run = True
        self._startat = datetime.now()
        self._schedule()

    def stop(self):
        if self._timer:
            self._timer.cancel()
        self._run = False

    def _schedule(self):
        self._timer = Timer(self._interval, self._runjob)
        self._timer.setDaemon(True)
        self._timer.start()

    def _runjob(self):
        try:
            self._count += 1
            logging.info('execute %d times', self._count)
            self._clean_old_data()
        except BaseException as e:
            logging.exception('fail to run clean job , count=%s', self._count)
        finally:
            if self._run:
                self._schedule()

    @model.dao
    def _clean_old_data(self, cursor):
        for tbl, days  in self._policy.items():
            logging.info('start to keep data of %s within %s days', tbl, days)
            theday = datetime.now() - timedelta(days=days)
            cursor.execute('DELETE FROM %s WHERE recv_at <= ?' % tbl, [theday])


class Master(object):
    """Agent work as the service and received status report from every Agent."""

    def __init__(self, config):
        servercfg = config['master']['server']
        self._stopped = False
        self._addr = (servercfg['host'], servercfg['port'])
        self._agents = None
        self._handlers = {}
        self._serversock = None
        self._agentsocks = {}
        self._init_handlers()
        self._load_agents()

        retentioncfg = config['master']['data_retention']
        self._data_keeper = DataKeeper(retentioncfg)
        self._data_keeper.start()
        self._alarm_engine = AlarmEngine()
        self._alarm_engine.start()
        logging.info('master init on addr=%s', self._addr)

    def _init_handlers(self):
        self._handlers[Msg.A_REG] = getattr(self, '_agent_reg')
        self._handlers[Msg.A_HEARTBEAT] = getattr(self, '_agent_heartbeat')
        self._handlers[Msg.A_NODE_METRIC] = getattr(self, '_agent_nmetrics')
        self._handlers[Msg.A_SERVICE_METRIC] = getattr(self, '_agent_smetrics')
        self._handlers[Msg.A_STOP] = getattr(self, '_agent_stop')
        logging.info('%s msg handlers prepared.', len(self._handlers))

    def _load_agents(self):
        agents = model.Agent.query()
        self._agents = {a.aid: a for a in agents}
        logging.info('load %d agents from db', len(agents))

    # Message handlers
    def _agent_reg(self, msg):
        agent = self.find_agent(msg.agentid)
        ahostname = msg.body['hostname']
        aname = ahostname + '@' + msg.body['os']
        if agent:
            agent.set(name=aname)
            logging.info('activate existing agent %s', agent)
            # TODO activation
        else:
            agent = model.Agent(msg.agentid, aname, ahostname, create_at=datetime.utcnow())
            agent.save()
            logging.info('new agent %s registered', agent)
            self._agents[agent.aid] = agent
        return True

    def _agent_heartbeat(self, msg):
        agent = self.find_agent(msg.agentid)
        agent.set(last_msg_at=datetime.utcnow())
        logging.debug('heart beat get from %s', agent)
        return True

    def _agent_stop(self, msg):
        logging.info('stopping agent %s', msg.agentid)
        sock = self._agentsocks.get(msg.agentid, None)
        if sock:
            sock.close()
            logging.info('agent %s stopped',  msg.agnetid)
        else:
            logging.warn('agent not active, invalid STOP message %s', msg)

    def _agent_nmetrics(self, msg):
        logging.debug('parsing node metrics message %s', msg)
        aid = msg.agentid
        agent = self._agents.get(aid)
        body = msg.body
        collect_time = msg.collect_at

        metrics = map(lambda x: model.NMetric(aid, collect_time, x[0], x[1], datetime.utcnow()), body.items())
        model.NMetric.save_all(metrics)

        memrep, cpurep, sysrep = None, None, None
        if 'free' in body:
            memrep = content_parser.parse_free(aid, collect_time, body['free'])
            memrep.save() if memrep else None
        if 'vmstat' in body:
            cpurep, procs_r, procs_b, sys_in, sys_cs \
                = content_parser.parse_vmstat(aid, collect_time, body['vmstat'])
            cpurep.save() if cpurep else None
        if 'w' in body:
            sysrep = content_parser.parse_w(aid, collect_time, body['w'])
            if sysrep:
                sysrep.procs_r = procs_r
                sysrep.procs_b = procs_b
                sysrep.sys_in = sys_in
                sysrep.sys_cs = sys_cs
                sysrep.save()
        if 'df' in body:
            dfreps = content_parser.parse_df(aid, collect_time, body['df'])
            if dfreps:
                model.NDiskReport.save_all(dfreps)
        if 'ip-link' in body:
            traffreps = content_parser.parse_iplinkstat(aid, collect_time, body['ip-link'])
            model.NNetworkReport.save_all(traffreps) if traffreps else None
        last_cpu_util = cpurep.used_util if cpurep else None
        last_mem_util = memrep.used_util if memrep else None
        last_sys_load1, last_sys_cs = (sysrep.load1, sysrep.sys_cs) if sysrep else (None, None)
        agent.set(last_msg_at=datetime.utcnow(),
                  last_cpu_util=last_cpu_util,
                  last_mem_util=last_mem_util,
                  last_sys_load1=last_sys_load1,
                  last_sys_cs=last_sys_cs)
        return True

    def _agent_smetrics(self, msg):
        aid = msg.agentid
        collect_at = msg.collect_at
        body = msg.body
        sname = body['name']
        spid = body['pid']
        stype = body.get('type', None)
        smetrics = [model.SMetric(aid, collect_at, sname, spid, mname, mcontent, datetime.utcnow())
                    for mname, mcontent in body['metrics'].items()]
        model.SMetric.save_all(smetrics)

        # calculate node services
        services = {s.name: s for s in model.SInfo.query_by_aid(aid)}
        if sname not in services:
            # service discovered
            logging.info('service %s discovered with pid %s', sname, spid)
            ser = model.SInfo(id=uuid4().hex, aid=aid, name=sname, pid=spid, type=stype,
                        last_report_at=collect_at, status=model.SInfo.STATUS_ACT).save()
            ser.add_history(collect_at)
        else:
            # existing service, check for an update
            ser = services[sname]
            logging.debug('refreshing service %s', ser)
            ser.set(last_report_at=collect_at, status=model.SInfo.STATUS_ACT)
            if ser.pid != int(spid):
                logging.info('service [%s] pid change detected: %s -> %s', sname, ser.pid, spid)
                ser.chgpid(spid, collect_at)

        # set service to inactive if no status update for 5 minutes
        for sname, service in services.items():
            active = service.chkstatus(300)  # 300 seconds
            if not active:
                logging.info('service %s turn to inactive.', service)

        self._parse_smetrics(smetrics, ser)
        return True

    def _parse_smetrics(self, metrics, service):
        for metric in metrics:
            logging.info('parsing %s for %s', metric.category, service)
            if 'pidstat' == metric.category:
                pidrep = content_parser.parse_pidstat(metric.aid, metric.collect_at, service.id, metric.content)
                pidrep.save() if pidrep else None
            if 'prstat' == metric.category:
                rep = content_parser.parse_prstat(metric.aid, metric.collect_at, service.id, metric.content)
                rep.save() if rep else None
            if 'jstat-gc' == metric.category:
                gcrep = content_parser.parse_jstatgc(metric.aid, metric.collect_at, service.id, metric.content)
                gcrep.save() if gcrep else None

    def find_agent(self, aid):
        agent = self._agents.get(aid, None)
        if agent is None:
            logging.warn('can not find agent %s form cache/db', aid)
        return agent

    def start(self):
        serversock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        serversock.bind(self._addr)
        serversock.setblocking(False)
        serversock.listen(64)
        logging.info('master started and bind/listen to %s', self._addr)
        self._serversock = serversock
        
        # staring loop
        logging.info('master is running.....')
        while not self._stopped:
            agentsocks = self._agentsocks.values()
            rlist, wlist, elist = select.select([self._serversock] + agentsocks, [], [], 5)
            for rsock in rlist:
                if rsock == self._serversock:
                    agentsocket, addr = rsock.accept()
                    self._agentsocks[addr] = agentsocket
                    logging.info('client socket %s connected', addr)
                else:
                    # read from client socket
                    self.recv_msg(rsock.getpeername())

    def recv_msg(self, addr):
        sock = self._agentsocks[addr]
        msg = read_agent_msg(sock)
        if msg:
            if not self.find_agent(msg.agentid) and msg.msg_type != Msg.A_REG:
                logging.info('agent(%s) not registered, message %s will skipped.', msg.agentid, msg)
                return
            else:
                return self.handle_msg(msg)
        else:
            logging.warn('unsupported msg get from %s',  addr)

    def handle_msg(self, msg):
        logging.info('handle msg %s', msg)
        handler = self._handlers.get(msg.msg_type, None)
        if handler:
            return handler(msg)
        else:
            logging.error('no handler defined for msg type %s', msg.msg_type)
            return

    def stop(self):
        for sock in self._agentsocks.values():
            try:
                sock.close()
            except socket.error:
                logging.warn('error while close agent socket %s', sock.getpeername())
        self._serversock.close()
        logging.info('server socket closed.')


def master_main(cfg):
    set_logging('master.log')
    basepath = os.path.dirname(sys.path[0])
    schemapath = os.path.join(basepath, 'conf', 'schema.sql')
    dbcfg = cfg['master']['database']
    model.init_db(dbcfg, schemapath)
    global _MASTER
    m = Master(cfg)
    m.start()


if __name__ == '__main__':
    basepath = os.path.dirname(sys.path[0])
    master_main(YAMLConfig(os.path.join(basepath, 'conf', 'master.yaml')))