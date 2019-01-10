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
import Queue as Q
import content_parser
import model
from datetime import datetime, timedelta
from threading import Timer, Thread, RLock
from uuid import uuid4
from common import YAMLConfig, Msg, set_logging, read_msg, send_msg, load_json


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


class AgentManger(object):
    """
    Manage agnet registration/de-regsitration and message exchanges.
    """
    def __init__(self, server_addr, message_handler):
        self._server_addr = server_addr
        self._message_handler = message_handler
        self._serversock = None
        self._stopped = False
        self._agentslock = RLock()
        self._agentsocks = {}
        self._sendq = Q.Queue()
        self._msg_receiver = Thread(name='Agent Message Receiver', target=self._recv_msg)
        self._msg_sender = Thread(name='Agent Message Sender', target=self._send_message)
        logging.info('agent manager init with addr %s, messgae handler %s', server_addr, message_handler)

    def _find_agent(self, agentid):
        agent = model.Agent.get_by_id(agentid)
        if agent is None:
            logging.warn('cant not find agent from db by aid %s', agentid)
        return agent

    def start(self, blocking=True):
        serversock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        serversock.bind(self._server_addr)
        serversock.setblocking(False)
        serversock.listen(64)
        logging.info('agent manager started, listening on %s', self._server_addr)
        self._serversock = serversock

        self._msg_receiver.daemon = False
        self._msg_sender.daemon = False
        self._msg_receiver.start()
        self._msg_sender.start()

    def _recv_msg(self):
        # staring loop
        logging.info('message receiver starting with stop flag is %s', self._stopped)
        while not self._stopped:
            logging.debug('message receiver is running...')
            agentsocks = self._agentsocks.values()

            rlist, wlist, elist = select.select([self._serversock] + agentsocks, [], [], 5)
            for rsock in rlist:
                try:
                    if rsock == self._serversock:
                        agentsocket, addr = rsock.accept()
                        self._agentsocks[addr] = agentsocket
                        logging.info('agent from %s connected', addr)
                    else:
                        # read from client socket
                        msg = read_msg(rsock)
                        if msg:
                            if not self._find_agent(msg.agentid) and msg.msg_type != Msg.A_REG:
                                logging.info('agent(%s) not registered, message %s will skipped.', msg.agentid, msg)
                            else:
                                self._message_handler(msg, rsock.getpeername())
                        else:
                            logging.warn('unsupported msg get from %s',  rsock.getpeername())
                except Exception as e:
                    if rsock == self._serversock:
                        logging.exception('error while accept new agent')
                    else:
                        logging.exception('error while recv message from %s, stop remote agent socket', rsock.getpeername())
                        self.stop_agent(rsock.getpeername())
        logging.info('message receiver stopped')

    def pub_msg(self, remote_addr, msg):
        logging.debug('put message %s to send queue with qsize = %s', msg, self._sendq.qsize())
        self._sendq.put((remote_addr, msg))

    def _send_message(self):
        logging.info('message sender is starting...')
        while not self._stopped:
            try:
                remote_addr, msg = self._sendq.get()
                sock = self._agentsocks.get(remote_addr, None)
                if sock is None:
                    logging.warn('agent socket not found by %s', remote_addr)
                else:
                    logging.info('pub msg to agent %s', remote_addr)
                    send_msg(sock, msg)
            except Exception as e:
                logging.exception('error while send message to %s', remote_addr)
                self.stop_agent(remote_addr)
        logging.info('message sender stopped')

    def stop_agent(self, remote_addr):
        with self._agentslock:
            sock = self._agentsocks.get(remote_addr, None)
            if sock is None:
                logging.warn('agent socket not found by %s', remote_addr)
            else:
                logging.info('stopping agent socket %s', remote_addr)
                try:
                    sock.close()
                except sock.error:
                    pass
                del self._agentsocks[remote_addr]

    def stop(self):
        self._stopped = True
        self._serversock.close()


class Master(object):
    """Agent work as the service and received status report from every Agent."""

    def __init__(self, config):
        servercfg = config['master']['server']
        self._stopped = False
        self._agents = None
        self._agent_addrs = {}
        self._handlers = {}
        self._init_handlers()
        self._load_agents()
        server_addr = (servercfg['host'], servercfg['port'])
        self._agent_manager = AgentManger(server_addr, self.handle_msg)

        retentioncfg = config['master']['data_retention']
        self._data_keeper = DataKeeper(retentioncfg)
        self._alarm_engine = AlarmEngine()

    def _load_agent_config(self):
        basepath = os.path.dirname(sys.path[0])
        agent_config = os.path.join(basepath, 'nodemonitor', 'agent_config.json')
        with open(agent_config) as f:
            return load_json(f.read())

    def _init_handlers(self):
        self._handlers[Msg.A_REG] = getattr(self, '_agent_reg')
        self._handlers[Msg.A_HEARTBEAT] = getattr(self, '_agent_heartbeat')
        self._handlers[Msg.A_NODE_METRIC] = getattr(self, '_agent_nmetrics')
        self._handlers[Msg.A_SERVICE_METRIC] = getattr(self, '_agent_smetrics')
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
        config_version = msg.body.get('config_version', None)
        curr_config = self._load_agent_config()
        curr_config_version = curr_config['version']
        if config_version is None or curr_config_version > config_version:
            logging.info(
                'current config version is %s, agent %s config version is %s, will update config to agent.',
                curr_config_version, agent.name, config_version)
            agent_addr = self._agent_addrs.get(msg.agentid)
            if agent_addr is None:
                logging.warn('can not find agnet addr for %s, config update msg will be disgarded', msg.agentid)
            else:
                cfgmsg = Msg.create_msg(msg.agentid, Msg.M_CONFIG_UPDATE, {'config': curr_config})
                self._agent_manager.pub_msg(agent_addr, cfgmsg)
                logging.info('config message %s send to %s', cfgmsg, agent_addr)
        logging.debug('heart beat get from %s', agent)
        return True

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

    def handle_msg(self, msg, agent_addr):
        logging.info('handle msg %s from %s', msg, agent_addr)
        self._agent_addrs[msg.agentid] = agent_addr
        handler = self._handlers.get(msg.msg_type, None)
        if handler:
            return handler(msg)
        else:
            logging.error('no handler defined for msg type %s', msg.msg_type)
            return

    def start(self):
        self._data_keeper.start()
        self._alarm_engine.start()
        self._agent_manager.start()

    def stop(self):
        self._agent_manager.stop()
        self._alarm_engine.stop()
        logging.info('master stopped.')


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