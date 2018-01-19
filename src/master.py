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
import collections
import socket
import SocketServer
import sqlite3
from multiprocessing import Process
from common import *
from master_ui import ui_main


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
_FILES_TO_COPY = ['common.py', 'agent.py', 'agent.json']
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
        self.ssh.exec_command('cd nodem && nohup python ./agent.py %s > agent.log 2>&1 & ' % (mhost,))
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


def master_main():
    global _MASTER
    _MASTER = Master('0.0.0.0')
    _MASTER.start()


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
        push_to_nodes([('cycad.ip.lab.chn.arrisi.com', 'root', 'no$go^'),
                       ('saaszdev107.ip.lab.chn.arrisi.com', 'root', 'no$go^')])
    else:
        master_proc = Process(target=master_main)
        masterui_proc = Process(target=ui_main)
        master_proc.start()
        logging.info('master backend process started: %s', master_proc)
        masterui_proc.start()
        logging.info('master ui process started: %s', masterui_proc)

        master_proc.join()
        masterui_proc.join()
        logging.info('master exited.')