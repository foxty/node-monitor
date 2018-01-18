#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Created on 2017-12-22
@author: foxty

Node monitor master:
- Monitor node health (CPU, IO, Memory, Load)
- Monitor specified processes (CPU, IO, Memory, Pidstat and logs)

"""
import os
import sys
import re
import logging
import base64
import collections
import json, json.decoder
from datetime import datetime, date, time
from struct import *
import socket
import SocketServer
import select
import Queue as Q
import threading
from subprocess import check_output, call
import sqlite3


# ==============================
#   Common Area (Agent & Master)
# ==============================
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(threadName)s:%(levelname)s:%(name)s:%(funcName)s:%(message)s')
_DATETIME_FMT = '%Y-%m-%d %H:%M:%S.%f'
_DATETIME_RE = re.compile('^\\d{4}-\\d{1,2}-\\d{1,2} \\d{2}:\\d{2}:\\d{2}\\.\\d{6}$')
_DATE_FMT = '%Y-%m-%d'
_DATE_RE = re.compile('^\\d{4}-\\d{1,2}-\\d{1,2}$')
_TIME_FMT = '%H:%M:%S.%f'
_TIME_RE = re.compile('^\\d{2}:\\d{2}:\\d{2}\\.\\d{6}$')


class ConfigError(Exception):
    pass


class SetupError(Exception):
    pass


class OSNotSupportError(Exception):
    pass


class InvalidMsgError(Exception):
    pass


class Msg(object):
    """A msg object present msg exchange between agent and master,
    a set of builtin encoder & decoder method provided to trans msg over TCP stream.
    """
    NONE = 'NONE'
    # management msg
    A_REG = 'A_REG'
    A_HEARTBEAT = 'A_HEARTBEAT'
    A_STOP = 'A_STOP'
    M_ACT = 'A_ACT'
    # metrics
    A_NODE_METRIC = 'A_NODE_METRIC'
    A_SERVICE_METRIC = 'A_SERVICE_METRIC'

    def __init__(self, agentid, mtype=NONE, sendtime=datetime.now(), headers=None, body=""):
        self._headers = {
            'AgentID': agentid,
            'MessageType': mtype,
            'SendTime': sendtime.strftime(_DATETIME_FMT),
        }
        if headers:
            self._headers.update(headers)
        self._body = body

    @property
    def agentid(self):
        return self._headers['AgentID']

    @property
    def msg_type(self):
        return self._headers['MessageType']

    @msg_type.setter
    def msg_type(self, value):
        self._headers['MessageType'] = value

    @property
    def sendtime(self):
        return datetime.strptime(self._headers['SendTime'], _DATETIME_FMT)

    @property
    def body(self):
        return self._body

    @body.setter
    def body(self, value):
        self._body = value
        self._headers['BodyLength'] = len(self._body)

    def encode(self):
        """encode msg to list of headers and body content.
        e.g:
        [MSG:A_REG, AgentID:xxxxxxx, SendTime:YYYYMMDD HH:mm:ss, BodyLength:12345], <body>
        """
        head = map(lambda x: '%s:%s' % x, self._headers.items())
        encbody = base64.b64encode(self._body)
        head.append('BodyLength:%d' % len(encbody))
        return head, encbody

    def __eq__(self, other):
        if isinstance(other, Msg):
            return other.agentid == self.agentid and\
                   other.msg_type == self.msg_type and \
                   other.body == self.body
        else:
            return False

    def __str__(self):
        return '%s->%s'%(self.msg_type, self.body)

    @classmethod
    def decode(cls, header_list=[], body=''):
        headers = {h[:h.index(':')] : h[h.index(':') + 1:] for h in header_list}
        body = base64.b64decode(body)
        return Msg(None, headers=headers, body=body)


class OSType(object):
    WIN = 1
    LINUX = 2
    SUNOS = 3


class TextTable(object):
    """convert a tabular data form text to table.
    e.g will convert follow data:

    a b c d\n
    1 2 3 5\n

    to
    [
     ['a','b','c','d'],
     ['1','2','3','4']
    ]

    """
    def __init__(self, content, header_ln=0, vheader = False):
        self._table = [[ele.strip() for ele in l.strip().split(' ') if ele.strip()]
                       for l in content.splitlines() if l.strip()]
        self._size = len(self._table)
        self._hheader = self._table[header_ln] if self.size > header_ln else None
        if vheader:
            self._vheader = [row[0] for row in self._table]

    @property
    def size(self):
        return self._size

    def gets(self, rowid, header, conv_func=str):
        """get values for header_name in row #rowno,
        :param rowid: row number or row name
        :param header: header name
        :param default: default value if header not exist
        :return: list of values (in case multi columns has same header name)
        """
        rowno = rowid if type(rowid) is int else self._vheader.index(rowid)
        idxs = []
        start = 0
        while True:
            try:
                idx = self._hheader.index(header, start)
                idxs.append(idx)
                start = idx + 1
            except ValueError as e:
                break
        return [conv_func(self._table[rowno][idx]) for idx in idxs]

    def get(self, rowno, header, default=None, conv_func=str):
        values = self.gets(rowno, header, conv_func=conv_func)
        return values[0] if values else default

    def get_ints(self, rowno, header):
        return self.gets(rowno, header, conv_func=int)

    def get_int(self, rowno, header, default=None):
        return self.get(rowno, header, default, conv_func=int)

    def get_floats(self, rowno, header):
        return self.gets(rowno, header, conv_func=float)

    def get_float(self, rowno, header, default=None):
        return self.get(rowno, header, default, conv_func=float)


def ostype():
    if "win" in sys.platform:
        return OSType.WIN
    elif "linux" in sys.platform:
        return OSType.LINUX
    elif "sunos" in sys.platform:
        return OSType.SUNOS
    else:
        raise OSNotSupportError()


def is_win():
    return ostype() == OSType.WIN


def is_linux():
    return ostype() == OSType.LINUX


def is_sunos():
    return ostype() == OSType.SUNOS


def dump_json(obj):
    """customized json encoder function to support datetime, date, time object"""
    def dt_converter(o):
        if isinstance(o, datetime):
            return o.strftime(_DATETIME_FMT)
        elif isinstance(o, date):
            return o.strftime(_DATE_FMT)
        elif isinstance(o, time):
            return o.strftime(_TIME_FMT)
        else:
            raise TypeError('Object %s not supporot by JSON encoder', o)

    return json.dumps(obj, default=dt_converter)


def load_json(str):
    """customized json decoder function to support datetime, date, time object"""

    def decode_date(v):
        if isinstance(v, basestring):
            if _DATETIME_RE.match(v):
                return datetime.strptime(v, _DATETIME_FMT)
            elif _DATE_RE.match(v):
                return datetime.strptime(v, _DATE_FMT)
            elif _TIME_RE.match(v):
                return datetime.strptime(v, _TIME_FMT)
            else:
                return v
        else:
            return v

    def obj_hook(dct):
        return {k: decode_date(v) for k, v in dct.items()}

    return json.loads(str, object_hook=obj_hook)


# ==============================
#   Node Agent
# ==============================
_MAX_BACKOFF_SECOND = 60  # in agent retry policy


class AgentConfig(object):

    def __init__(self, cfgpath):
        if not os.path.exists(cfgpath) or not os.path.isfile(cfgpath):
            raise ConfigError('%s not found'%cfgpath)
        with open(cfgpath) as f:
            config = json.load(f)
        self._node_metrics = config.get('node_metrics', {})
        self._valid_node_metrics = None
        self._service_metrics = config.get('service_metrics', {})
        self._valid_service_metrics = None
        self._services = config.get('services',[])
        self._valid_services = None
        self._validate()

        self._hb_interval = 30 # seconds
        self._nmetrics_interval = 60 # seconds
        self._smetrcis_interval = 300 # seconds

    def _validate(self):
        checkcmd = 'where' if is_win() else 'which'
        # check node metrics
        logging.info('check node command by %s', checkcmd)
        self._valid_node_metrics = {k: v for k, v in self._node_metrics.items()
                                    if call([checkcmd, v[0]]) == 0}
        logging.info('valid node metrics = %s', self._valid_node_metrics)

        # check service metrics
        logging.info('check service command by %s', checkcmd)
        self._valid_service_metrics = {k: v for k, v in self._service_metrics.items()
                                       if call([checkcmd, v[0]]) == 0}
        logging.info('valid service metrics = %s', self._valid_service_metrics)

        # check services
        invalid_serivces = [s for s in self._services if 'name' not in s or 'lookup' not in s]
        self._valid_services = [s for s in self._services if s not in invalid_serivces] \
            if invalid_serivces else self._services
        logging.info('valid service=%s, invalid services=%s',
                     map(lambda x: x['name'], self._valid_services),
                     invalid_serivces)

    @property
    def valid_node_metrics(self):
        return self._valid_node_metrics

    @property
    def valid_service_metrics(self):
        return self.valid_service_metrics

    @property
    def valid_services(self):
        return self._valid_services

    @property
    def hb_interval(self):
        return self._hb_interval

    @property
    def nmetrics_interval(self):
        return self._nmetrics_interval

    @property
    def smetrics_interval(self):
        return self._smetrcis_interval


class NodeCollector(threading.Thread):

    def __init__(self, agent, config):
        super(NodeCollector, self).__init__(target=self._collect, name='NodeCollector')
        self._agent = agent
        self._agentid = agent.agentid
        self._def_interval = 10
        self._delay = threading.Event()
        self._config = config
        self.setDaemon(True)

    def _collect(self):
        interval = self._def_interval
        hb_loop = self._config.hb_interval / interval
        nmetrics_loop = self._config.nmetrics_interval / interval
        smetrics_loop = self._config.smetrics_interval / interval
        loops = 1;
        while True:
            self._delay.wait(interval)
            time1 = datetime.now()
            try:
                if loops % hb_loop == 0:
                    self._prod_heartbeat()
                if loops % nmetrics_loop == 0:
                    self._collect_nmetrics()
                if loops % smetrics_loop == 0:
                    self._collect_smetrics()
            except BaseException as e:
                logging.exception('error during collect metrics, wait to next round. %s', e)
            finally:
                loops = loops + 1
            time2 = datetime.now()
            time_used = (time2 - time1).seconds
            interval = self._def_interval - time_used

    def _prod_heartbeat(self):
        logging.info('produce heartbeat...')
        body = {'datetime': datetime.now()}
        hb_msg = Msg(self._agentid, Msg.A_HEARTBEAT, body=dump_json(body))
        self._agent.add_msg(hb_msg)

    def _collect_nmetrics(self):
        """Collect node metrics"""
        logging.info('collecting node metrics...')
        result = {}
        for k, cmd in self._config.valid_node_metrics.items():
            try:
                output = check_output(cmd)
                result[k] = output
            except BaseException as e:
                logging.exception('call cmd %s failed', cmd)
                result[k] = e.message
        result['collect_time'] = datetime.now().strftime(_DATETIME_FMT)
        nm_msg = Msg(self._agentid, Msg.A_NODE_METRIC, body=dump_json(result))
        self._agent.add_msg(nm_msg)

    def _find_services(self):
        logging.info('service discovery...')
        act_services = {}
        for s in self._config.valid_services:
            sname = s['name']
            slookup = s['lookup']
            logging.info('try to lookup service %s', sname)
            try:
                pid = check_output(slookup)
                if pid and pid.isdigit():
                    s['pid'] = pid
                    act_services[sname] = s
                else:
                    logging.info('can\'t lookup pid for %s', sname)
            except BaseException as e:
                logging.error('look up service %s by %s failed', sname, slookup)
        return act_services

    def _collect_smetrics(self):
        """Collect services metrics"""
        result = {}
        services = self._find_services()
        logging.info('collecting services metrics for %s...', ','.join(services.keys()))
        for sname, s in services.items():
            pid = s['pid']
            for sm_name, sm_cmd in self._config.valid_service_metrics.items():
                print sm_name, sm_cmd


class NodeAgent:
    """Agent will running the node as and keep send stats data to Master via TCP connection."""

    _SENDQ = Q.Queue(maxsize=2)

    def __init__(self, master_host='localhost', master_port=7890, configfile="./agent.json"):

        if not os.path.isfile(configfile):
            raise ConfigError('agent can not find any config file in %s', configfile)

        self._hostname = socket.gethostname()
        self._agentid = self._gen_agentid()
        self._master_addr = (master_host, master_port)
        self._started = False
        self._retry = threading.Event()
        self._config = AgentConfig(configfile)
        self._stat_collector = NodeCollector(self, self._config)
        logging.info('agent init with id=%s, master=%s, config=%s, hostname=%s',
                     self._agentid, self._master_addr, configfile, self._hostname)

    @property
    def agentid(self):
        return self._agentid

    def _gen_agentid(self):
        if ostype() == OSType.WIN:
            return self._hostname[0:8] if len(self._hostname) >= 8 else self._hostname.ljust(8, 'x')
        else:
            hostid = check_output(['hostid'])
            return hostid[0:8] if len(hostid) >= 8 else hostid.ljust(8, 'x')

    def _connect_master(self):
        if getattr(self, 'sock', None):
            logging.warn('Found exiting socket, now close it.')
            try:
                self.sock.close()
            except:
                pass

        logging.info('connecting to master %s', self._master_addr)
        tried = 0
        while 1:
            tried = tried + 1
            try:
                sock = socket.create_connection(self._master_addr, 5)
                sock.setblocking(False)
                break
            except socket.error as e:
                sleeptime = min(_MAX_BACKOFF_SECOND, tried ** 2)
                logging.warn('Cannot connect %s(tried=%d) due to %s, will retry after %d seconds...',
                             self._master_addr, tried, e, sleeptime)
                self._retry.wait(sleeptime)
        logging.info('connect to master %s succed.', self._master_addr)
        self.sock = sock
        # do agent_reg
        self._do_reg()

    def start(self):
        logging.info('agent %s starting ...', self._agentid)
        self._connect_master()
        self._stat_collector.start()
        self._started = True
        self._loop()

    def stop(self):
        self._started = False
        self.sock.close()
        logging.info('agent %s stopped.', self._agentid)

    def add_msg(self, msg):
        """Add new msg to the queue and remove oldest msg if its full"""
        retry = 0
        while True:
            try:
                if self._SENDQ.full():
                    oldest_msg = self._SENDQ.get_nowait()
                    logging.debug('q is full, msg %s abandoned, qsize=%d.',
                                  oldest_msg, self._SENDQ.qsize())
                self._SENDQ.put_nowait(msg)
                logging.debug('msg %s added to queue, retry=%d, qsize=%d.',
                              msg, retry, self._SENDQ.qsize())
                break;
            except Q.Full:
                # Queue is full, retry
                retry += 1


    def _do_reg(self):
        """Produce a agent reg message after connected"""
        logging.info('do registration...')
        osname = os.name
        reg_msg = Msg(agentid=self._agentid, mtype=Msg.A_REG, body=dump_json(osname))
        self.add_msg(reg_msg)

    def _loop(self):
        logging.info('start agent looping...')
        while self._started:
            sock_list = [self.sock]
            try:
                rlist, wlist, elist = select.select([], sock_list, sock_list)
                if rlist: self._do_read(rlist[0])
                if wlist: self._do_write(wlist[0])
                if elist: self._do_error(elist[0])
            except socket.error as se:
                logging.exception(se)
                self._connect_master()
            except InvalidMsgError as ime:
                logging.error(ime)
                self.stop()

    def _do_read(self, sock):
        rdata = sock.recv(1024)
        if not rdata:
            raise InvalidMsgError('get invalid msg ' + rdata + ' from master')
        else:
            logging.info('get data %s from master', rdata.strip())

    def _do_write(self, sock):
        if not self._SENDQ.empty():
            try:
                msg = self._SENDQ.get_nowait()
            except Q.Empty as e:
                logging.warn('Try to get msg from empty queue..')
                return
            headers, body = msg.encode()
            headers.append(body)
            data = '\n'.join(headers)
            datalen = len(data)
            sock.send('MSG:%d\n' % datalen)
            size = sock.send(data)
            logging.debug('send msg type=%s, datalen=%d, size=%d, to=%s',
                          msg.msg_type, datalen, size, self._master_addr)

    def _do_error(self, sock):
        logging.debug('error')


# ==============================
#   Node Master
# ==============================
# Global status for Master
_MASTER = None
_MASTER_DB_NAME = 'master.db'
_AGENT_FIELDS = 'aid, name, host, created_at'
_NMETRIC_FIELDS = 'aid, collect_at, category, content, created_at'
_NMEM_FIELDS = 'aid, collect_at, total_mem, used_mem, free_mem, cache_mem, total_swap, used_swap, free_swap'
_NCPU_FIELDS = 'aid, collect_at, us, sy, id, wa, st'
_NSYS_FIELDS = 'aid, collect_at, uptime, users, load1, load5, load15, procs_r, procs_b, sys_in, sys_cs'

Agent = collections.namedtuple('Agent', _AGENT_FIELDS)
NMetric = collections.namedtuple('NMetric', _NMETRIC_FIELDS)
NMemoryReport = collections.namedtuple('NMemoryReport', _NMEM_FIELDS)
NCPUReport = collections.namedtuple('NCPUReport', _NCPU_FIELDS)
NSystemReport = collections.namedtuple('NSystemReport', _NSYS_FIELDS)


def dao(f):
    def dao_decorator(*kargs, **kdargs):
        with sqlite3.connect(_MASTER_DB_NAME,
                             detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES) as conn:
            c = conn.cursor()
            kdargs['cursor'] = c
            r = f(*kargs, **kdargs)
            conn.commit()
            c.close()
        return r
    return dao_decorator


_RE_SYSREPORT = re.compile('.*?(?P<days>\\d+)\\s+day.*?(?P<users>\\d+)\\suser.*'
                           'age: (?P<load1>\\d+\\.\\d+), (?P<load5>\\d+\\.\\d+), (?P<load15>\\d+\\.\\d+).*',
                           re.S)


def parse_w(aid, collect_time, content):
    """parse the output of w command as follow:
     21:25:14 up 45 days,  3:18,  1 user,  load average: 0.00, 0.03, 0.05
    USER     TTY      FROM             LOGIN@   IDLE   JCPU   PCPU WHAT
    root     pts/0    pc-itian.arrs.ar 27Dec17  2.00s  8:47   0.00s w
    :param aid: agentid
    :param collect_time: collect time from node
    :param content: output of `w`
    :return: NSystemReport
    """
    m = _RE_SYSREPORT.match(content)
    if m:
        days = int(m.group('days'))
        users = int(m.group('users'))
        load1 = float(m.group('load1'))
        load5 = float(m.group('load5'))
        load15 = float(m.group('load15'))
        return NSystemReport(aid, collect_time, uptime=days*24*3600, users=users,
                             load1=load1, load5=load5, load15=load15,
                             procs_r=None, procs_b=None, sys_in=None, sys_cs=None)
    else:
        return None


def parse_free(aid, collect_time, content):
    """parse output of `free -m` command get memory usage information:
                 total       used       free     shared    buffers     cached
    Mem:         19991       6428      13562          0        148       2656
    -/+ buffers/cache:       3623      16367
    Swap:        10063          0      10063

    :param aid: agentid
    :param collect_time: collect time from node
    :param content: output of `free -m`
    :return: NMemoryReport
    """
    t = TextTable('col ' + content.lstrip(), vheader=True)
    if t.size >= 2:
        total_mem = t.get_int('Mem:', 'total')
        used_mem = t.get_int('Mem:', 'used')
        free_mem = t.get_int('Mem:', 'free')
        total_swap = t.get_int('Swap:', 'total')
        use_swap = t.get_int('Swap:', 'used')
        free_swap = t.get_int('Swap:', 'free')
        return NMemoryReport(aid, collect_time, total_mem=total_mem, used_mem=used_mem,
                             free_mem=free_mem, cache_mem=None, total_swap=total_swap,
                             used_swap=use_swap, free_swap=free_swap)
    logging.warn('invalid output of free: %s', content)
    return None


def parse_vmstat(aid, collect_time, content):
    """parse output of command `vmstat` and extact the system/cpu section.

    Linux output:
    procs -----------memory---------- ---swap-- -----io---- --system-- -----cpu-----
     r  b   swpd   free   buff  cache   si   so    bi    bo   in   cs us sy id wa st
     0  0      0 13540540 161232 2972924    0    0     2    17   84   25  0  0 99  1  0
     0  0      0 13540532 161232 2972956    0    0     0    48  310  550  0  0 99  1  0

    Solaris output:
     kthr      memory            page            disk          faults      cpu
     r b w   swap  free  re  mf pi po fr de sr s0 s1 s2 --   in   sy   cs us sy id
     3 0 0 69302168 22126772 4 62 0 0  0  0  0 -0  0 33  0 2503 4393 3645  2  4 94
     1 0 0 68852484 24149452 11 53 0 0 0  0  0  0  0  0  0 1463 1273 1198  1  1 99

    :param aid:
    :param collect_time:
    :param content:
    :return: (NCPUReport, procs_r, procs_b, sys_in, sys_cs)
    """
    t = TextTable(content, 1)
    if t.size == 4:
        data_rn = -1
        procs_r, procs_b = t.get_int(data_rn,'r'), t.get_int(data_rn,'b')
        sys_in, sys_cs = t.get_int(data_rn,'in'), t.get_int(data_rn,'cs')
        us, sy = t.get_int(data_rn,'us'), t.get_ints(data_rn,'sy')[-1]
        id_, wa = t.get_int(data_rn,'id'), t.get_int(data_rn,'wa')
        st = t.get_int(data_rn,'st')
        r = NCPUReport(aid=aid, collect_at=collect_time,
                       us=us, sy=sy,id=id_, wa=wa, st=st)
        return r, procs_r, procs_b, sys_in, sys_cs
    logging.warn('invalid output of vmstat : %s', content)
    return None, None, None, None, None


class AgentStatus(object):

    def __init__(self, agent, client_addr=None, heartbeat_at=datetime.now(), active=False):
        self._agent = agent
        self._client_addr = client_addr
        self._heartbeat_at = heartbeat_at
        self._active = active

    @property
    def agent(self):
        return self._agent

    @property
    def client_addr(self):
        return self._client_addr

    @client_addr.setter
    def client_addr(self, v):
        self._client_addr = v

    @property
    def heartbeat_at(self):
        return self._heartbeat_at

    def heartbeat(self):
        self._heartbeat_at = datetime.now()
        self.activate()

    @property
    def active(self):
        return self._active

    def refresh(self):
        self._heartbeat_at = datetime.now()

    def inactive(self):
        self._active = False

    def activate(self):
        self._active = True

    def __eq__(self, other):
        if isinstance(other, AgentStatus):
            return other.agentid == self.agentid and \
                   other.client_addr == self.client_addr
        else:
            return False

    def __str__(self):
        return '[AgentStatus:agent=%s, addr=%s, active=%s]' % \
               (self._agent, self._client_addr, self._active)


class AgentRequestHandler(SocketServer.StreamRequestHandler):
    """All message are MonMsg and we should decode the msg here"""

    def handle(self):
        self.agentid = None
        try:
            self._loop()
        except Exception as e:
            logging.exception('error while processing data for %s', self.client_address)
        finally:
            status = _MASTER.inactive_agent(self.agentid)
            logging.info('agent %s quit', status)

    def _chk_msg(self, msg):
        if not _MASTER.find_agent(msg.agentid) and msg.msg_type != Msg.A_REG:
            raise InvalidMsgError('agentid %s not registered from %s',
                                  msg.agentid, self.client_address)
        elif not self.agentid:
            self.agentid = msg.agentid
            logging.info('new agent %s joined', self.client_address)
        elif self.agentid != msg.agentid:
            raise InvalidMsgError('agentid change detected %d->%d from %s',
                                  self.agentid, msg.agentid, self.client_address)

    def _recv_msg(self):
        header = self.rfile.readline().strip().split(':')
        if len(header) == 2 and 'MSG' == header[0] and header[1].isdigit():
            data = self.rfile.read(int(header[1])).split('\n')
            headers, body = data[:-1], data[-1]
            msg = Msg.decode(headers, body)
            msg.client_addr = self.client_address
            logging.debug("recv msg type=%s,datalen=%s,size=%d from %s",
                          msg.msg_type, header[1], len(data), self.client_address)
            return msg
        else:
            raise InvalidMsgError('unsupported msg header %s from %s'%(header, self.client_address))

    def _loop(self):
        process = True
        while process:
            msg = self._recv_msg()
            self._chk_msg(msg)
            process = _MASTER.handle_msg(msg)
            if not process:
                logging.info('msg handler stopped for %s from %s', msg, self.agentid)


class MasterDAO(object):
    """DAO for master use to manipulate data with database"""
    _DB_SCHEMA = r'''
    CREATE TABLE IF NOT EXISTS agent(aid UNIQUE, name, host, created_at timestamp);
    CREATE TABLE IF NOT EXISTS node_metric_raw(aid, collect_at timestamp, category, content, created_at timestamp);
    CREATE TABLE IF NOT EXISTS node_memory_report(
        aid, collect_at timestamp, total_mem, used_mem, 
        free_mem, cache_mem, total_swap, used_swap, free_swap);
    CREATE TABLE IF NOT EXISTS node_cpu_report(aid, collect_at timestamp, us, sy, id, wa, st);
    CREATE TABLE IF NOT EXISTS node_system_report(aid, collect_at timestamp, uptime, users, 
        load1, load5, load15, procs_r, procs_b, sys_in, sys_cs);
    '''

    def __init__(self, pool_size=5):
        self._pool_size = pool_size
        self._init_db()

    @dao
    def _init_db(self, cursor):
        cursor.executescript(self._DB_SCHEMA)

    @dao
    def add_agent(self, agent, cursor):
        cursor.execute('insert into agent (aid, name, host, created_at) values(?,?,?,?)'
                       , (agent.aid, agent.name, agent.host, agent.created_at))

    @dao
    def get_agents(self, cursor):
        cursor.execute('select * from agent')
        return [Agent(*a) for a in cursor.fetchall()]

    @dao
    def add_nmetrics(self, agentid, collect_time, contents, cursor):
        metrics = map(lambda x: (agentid, collect_time, x[0], x[1], datetime.now()), contents.items())
        logging.debug('add node metrics to db:agent=%s, collect_time=%s, recs=%d',
                      agentid, collect_time, len(metrics))
        cursor.executemany('INSERT INTO node_metric_raw (%s) VALUES (?,?,?,?,?)' % _NMETRIC_FIELDS, metrics)

    @dao
    def get_nmetrics(self, agentid, start, end=datetime.now(), category=None, cursor=None):
        cursor.execute('select %s from node_metric_raw '
                       'where aid=? and collect_at>=? and collect_at <=?' % _NMETRIC_FIELDS,
                       (agentid, start, end))
        return [NMetric(*r) for r in cursor.fetchall()]

    @dao
    def add_memreport(self, mem, cursor):
        logging.debug('add node memory report to db:%s', mem)
        cursor.execute('INSERT INTO node_memory_report (%s) VALUES (?,?,?,?,?,?,?,?,?)' % _NMEM_FIELDS,
                       mem)

    @dao
    def get_memreports(self, aid, start, end=datetime.now(), cursor=None):
        cursor.execute('select %s from node_memory_report '
                       'where aid=? and collect_at>=? and collect_at <=?' % _NMEM_FIELDS,
                       (aid, start, end))
        return [NMemoryReport(*r) for r in cursor.fetchall()]

    @dao
    def add_sysreport(self, s, cursor):
        cursor.execute('insert into node_system_report (%s) VALUES (?,?,?,?,?,?,?,?,?,?,?)' % _NSYS_FIELDS, s)
        logging.debug('add node sys report to db:%s', s)

    @dao
    def get_sysreports(self, aid, start, end=datetime.now(), cursor=None):
        cursor.execute('select %s from node_system_report '
                       'where aid=? and collect_at>=? and collect_at <=?' % _NSYS_FIELDS,
                       (aid, start, end))
        return [NSystemReport(*r) for r in cursor.fetchall()]

    @dao
    def add_cpureport(self, cpu, cursor):
        logging.debug('add node cpu report to db:%s', cpu)
        cursor.execute('INSERT INTO node_cpu_report (%s) VALUES (?,?,?,?,?,?,?)' % _NCPU_FIELDS, cpu)

    @dao
    def get_cpureports(self, aid, start, end=datetime.now(), cursor=None):
        cursor.execute('SELECT %s from node_cpu_report '
                       'WHERE aid=? AND collect_at>=? AND collect_at <=?' % _NCPU_FIELDS,
                       (aid, start, end))
        return [NCPUReport(*r) for r in cursor.fetchall()]

    @dao
    def add_smetrics(selfs, agentid, serv_name, contents):
        pass


class Master:
    """Agent work as the service and received status report from every Agent."""

    def __init__(self, host=socket.gethostname(), port=7890):
        self._addr = (host, port)
        self._agents = None
        self._handlers = {}
        self._dao = MasterDAO()
        self._server = None
        self._init_handlers()
        self._load_agents()
        logging.info('master init on addr=%s', self._addr)

    def _init_handlers(self):
        self._handlers[Msg.A_REG] = getattr(self, '_agent_reg')
        self._handlers[Msg.A_HEARTBEAT] = getattr(self, '_agent_heartbeat')
        self._handlers[Msg.A_NODE_METRIC] = getattr(self, '_agent_nmetrics')
        self._handlers[Msg.A_SERVICE_METRIC] = getattr(self, '_agent_smetrics')
        self._handlers[Msg.A_STOP] = getattr(self, '_agent_stop')
        logging.info('%s msg handlers prepared.', len(self._handlers))

    def _load_agents(self):
        agents = self._dao.get_agents()
        self._agents = {a.aid: AgentStatus(a) for a in agents}
        logging.info('load %d agents from db', len(agents))

    # Message handlers
    def _agent_reg(self, msg):
        agent_status = self._agents.get(msg.agentid, None)
        if agent_status:
            logging.info('activate existing agent %s', agent_status)
            agent_status.client_addr = msg.client_addr
            agent_status.activate()
            return True
        else:
            agent = Agent(msg.agentid, msg.client_addr[0], msg.client_addr[0], datetime.now())
            self._dao.add_agent(agent)
            agent_status = AgentStatus(agent, msg.client_addr, active=True)
            logging.info('new agent %s', agent_status)
            self._agents[agent.aid] = agent_status
            return True

    def _agent_heartbeat(self, msg):
        agentstatus = self.find_agent(msg.agentid)
        agentstatus.heartbeat()
        return True

    def _agent_nmetrics(self, msg):
        aid = msg.agentid
        body = load_json(msg.body)
        collect_time = body.pop('collect_time')
        self._dao.add_nmetrics(aid, collect_time, body)
        if 'free' in body:
            memrep = parse_free(aid, collect_time, body['free'])
            self._dao.add_memreport(memrep) if memrep else None
        if 'vmstat' in body:
            cpurep, procs_r, procs_b, sys_in, sys_cs \
                = parse_vmstat(aid, collect_time, body['vmstat'])
            self._dao.add_cpureport(cpurep) if cpurep else None
        if 'w' in body:
            sysrep = parse_w(aid, collect_time, body['w'])
            if sysrep:
                sysrep = sysrep._replace(procs_r=procs_r)
                sysrep = sysrep._replace(procs_b=procs_b)
                sysrep = sysrep._replace(sys_in=sys_in)
                sysrep = sysrep._replace(sys_cs=sys_cs)
            self._dao.add_sysreport(sysrep) if sysrep else None
        return True

    def _agent_smetrics(self, msg):
        return True

    def _agent_stop(self, msg):
        return True

    def find_agent(self, aid):
        return self._agents.get(aid, None)

    def start(self):
        logging.info('master started and listening on %s', self._addr)
        self._server = SocketServer.ThreadingTCPServer(self._addr, AgentRequestHandler)
        self._server.serve_forever()

    def handle_msg(self, msg):
        return self._handlers[msg.msg_type](msg)

    def inactive_agent(self, agentid):
        agent_status = self._agents[agentid]
        agent_status.inactive()
        return agent_status

    def stop(self):
        self._server.server_close()


# ==============================
#   Main and scripts
# ==============================
_FILES_TO_COPY = ['node_monitor.py', 'agent.json']
_INSTALL_PY27 = True
_FILE_OF_PY27 = 'Python-2.7.14.tgz'


class NodeConnector(object):
    """Using ssh connect to node and provide list of operation utils"""

    def __init__(self, node_host, username, password):
        self.node_host = node_host
        self.username = username
        self.password = password

    def __enter__(self):
        from paramiko import SSHClient, AutoAddPolicy
        self.ssh = SSHClient()
        self.ssh.set_missing_host_key_policy(AutoAddPolicy())
        logging.info('checking node %s', self.node_host)
        self.ssh.connect(hostname=self.node_host, username=self.username, password=self.password)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.ssh.close()
        logging.info('exit node collector from %s', self.node_host)

    def py27_installed(self):
        ins, ous, ers = self.ssh.exec_command('python -V')
        out_msg = ous.readline()
        err_msg = ers.readline()
        logging.debug('out=%s, err=%s', out_msg, err_msg)
        return 'Python 2.7' in (out_msg or err_msg)

    def install_py(self, filename):
        logging.info('install %s ...', filename)
        ins, outs, errs = self.ssh.exec_command('tar xvfz nodem/Python-2.7.14.tgz && cd Python-2.7.14 '
                                                '&& ./configure && make && make install && python2 -V')
        if self.py27_installed():
            logging.info('%s installed success.', filename)
        else:
            logging.error(errs.readlines())
            raise SetupError('Install py27 failed.')

    def trans_files(self, files=[]):
        with self.ssh.open_sftp() as sftp:
            dirs = sftp.listdir()
            if 'nodem' not in dirs:
                # already have nodem folder
                logging.info('nodem not exist in home, creat it')
                sftp.mkdir('nodem')
            logging.info('copying files %s to node', files)
            for f in files:
                sftp.put(f, 'nodem/' + f)
                logging.info('file %s transferred successfully', f)

    def launch_agent(self, mhost):
        """Launch remote agent via ssh channel"""
        logging.info('start agent on %s, master=%s', self.node_host, mhost)
        self.ssh.exec_command('cd nodem && nohup python ./node_monitor.py agent %s > agent.log 2>&1 & ' % (mhost,))
        logging.info('agnet started on host %s', mhost)

    def stop_agent(self):
        """Stop agent in remote node"""
        logging.info('try to stop agent on %s', self.node_host)
        self.ssh.exec_command("ps -ef|grep node_m | grep -v grep| awk '{print $2}' | xargs kill -9")
        logging.info('agent on %s stopped', self.node_host)


def download_py():
    """Download python installation package from www

    py2:https://www.python.org/ftp/python/2.7.14/Python-2.7.14.tgz
    py3:https://www.python.org/ftp/python/3.6.4/Python-3.6.4.tgz
    """
    logging.info('start download %s', _FILE_OF_PY27)
    import requests
    r = requests.get('https://www.python.org/ftp/python/2.7.14/Python-2.7.14.tgz')
    with file(_FILE_OF_PY27, 'wb') as f:
        f.write(r.content)


def push_to_nodes(nodelist):
    """push agent script to remote node and start the agent via ssh
    node list should contains list of tuple like (host, userame, password)
    """
    mhost = socket.gethostbyaddr(socket.gethostname())[0]
    for node in nodelist:
        host, user, password = node
        with NodeConnector(host, user, password) as nc:
            logging.info('checking node %s', host)
            need_py27 = _INSTALL_PY27 and not nc.py27_installed()
            if need_py27:
                if not os.path.exists(_FILE_OF_PY27):
                    download_py()
                nc.trans_files(_FILES_TO_COPY + [_FILE_OF_PY27])
                nc.install_py(_FILE_OF_PY27)
            else:
                nc.trans_files(_FILES_TO_COPY)
                logging.info('py27 already installed, skip installation process.')
            nc.stop_agent()
            nc.launch_agent(mhost)
    return nodelist


if __name__ == '__main__':

    # try:
    #     opts, args = getopt.getopt(sys.argv[:], "hma:", ['help', 'master', 'agent='])
    # except getopt.GetoptError as e:
    #     print('Wrong usage')
    #     sys.exit(2)
    #
    # for opt, v in opts:
    #     if opt in ['-m', '--master']:

    if 'push' in sys.argv:
        push_to_nodes([('cycad.ip.lab.chn.arrisi.com', 'root', 'no$go^')])
    elif 'master' in sys.argv:
        _MASTER = Master('0.0.0.0')
        _MASTER.start()
    elif 'agent' in sys.argv:
        mhost = sys.argv[2]
        agent = NodeAgent(mhost)
        agent.start()
    else:
        print('No action specified, exit.')
