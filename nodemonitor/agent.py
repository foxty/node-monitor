#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Created on 2017-12-22
@author: foxty

Node Agent
"""
# ==============================
#   Node Agent
# ==============================
import os
import sys
import logging
import getopt
import socket
import select
import re
import Queue as Q
import threading
from datetime import datetime
from subprocess import Popen, PIPE, call
from common import Msg, InvalidMsgError, is_win, is_sunos, ostype, OSType


_MAX_BACKOFF_SECOND = 60  # in agent retry policy


class CalledProcessError(Exception):
    """This exception is raised when a process run by check_call() or
    check_output() returns a non-zero exit status.

    Attributes:
      cmd, returncode, output
    """
    def __init__(self, returncode, cmd, output=None):
        self.returncode = returncode
        self.cmd = cmd
        self.output = output


    def __str__(self):
        return "Command '%s' returned non-zero exit status %d" % (self.cmd, self.returncode)


def check_output(*popenargs, **kwargs):
    r"""Run command with arguments and return its output as a byte string.

    If the exit code was non-zero it raises a CalledProcessError.  The
    CalledProcessError object will have the return code in the returncode
    attribute and output in the output attribute.

    The arguments are the same as for the Popen constructor.  Example:

    >>> check_output(["ls", "-l", "/dev/null"])
    'crw-rw-rw- 1 root root 1, 3 Oct 18  2007 /dev/null\n'

    The stdout argument is not allowed as it is used internally.
    To capture standard error in the result, use stderr=STDOUT.

    >>> check_output(["/bin/sh", "-c",
    ...               "ls -l non_existent_file ; exit 0"],
    ...              stderr=STDOUT)
    'ls: non_existent_file: No such file or directory\n'
    """
    if 'stdout' in kwargs:
        raise ValueError('stdout argument not allowed, it will be overridden.')
    process = Popen(stdout=PIPE, *popenargs, **kwargs)
    output, unused_err = process.communicate()
    retcode = process.poll()
    if retcode:
        cmd = kwargs.get("args")
        if cmd is None:
            cmd = popenargs[0]
        raise CalledProcessError(retcode, cmd, output=output)
    return output


def is_valid_exist(cmd):
    checkcmd = 'which'
    if is_win():
        checkcmd = 'where'
    if is_sunos():
        checkcmd = 'type'
    logging.info('check "%s" by "%s"', cmd, checkcmd)
    return call([checkcmd, cmd]) == 0


class AgentConfig(object):

    CONFIG = {
        "clock_interval": 10,
        "heartbeat_clocks": 6,
        "node_metrics": {
            "dstat-sys": {
                "cmd": ["dstat", "-lyp", "1", "1"],
                "clocks": 6
            },
            "dstat-cpu": {
                "cmd": ["dstat", "-c", "1", "1"],
                "clocks": 6
            },
            "dstat-mem": {
                "cmd": ["dstat", "-msg", "1", "1"],
                "clocks": 6
            },
            "dstat-socket": {
                "cmd": ["dstat", "--socket", "1", "1"],
                "clocks": 6
            },
            "dstat-dio": {
                "cmd": ["dstat", "-dr", "1", "1"],
                "clocks": 6
            },
            "w": {
                "cmd": ["w"],
                "clocks": 6
            },
            "free": {
                "cmd": ["free", "-m"],
                "clocks":6
            },
            "vmstat": {
                "cmd": ["vmstat","1", "2"],
                "clocks": 6
            },
            "netstat": {
                "cmd": ["netstat", "-s"],
                "clocks": 6
            },
            "df": {
                "cmd": ["df", "-kP"],
                "clocks":60
            }
        },

        "service_metrics": {
            "pidstat": {
                "type": "all",
                "cmd": ["pidstat", "-tdruh", "-p", "${pid}"]
            },
            "jstat-gc": {
                "type": "java",
                "cmd": ["${java_home}/bin/jstat", "-gc", "${pid}"]
            }
        },

        "services": [

            {
                "name": "agent",
                "type": "python",
                "lookup_keyword": "agent.py",
                "log_pattern": ["agent.log"],
                "metrics": ["pidstat"],
                "clocks": 6
            },

            {
                "name": "SAPM.Reactor@Linux",
                "type": "java",
                "lookup_keyword": "-Dreactor.home=/opt",
                "env" : {
                    "java_home": "/opt/arris/servassure/jdk1.8.0_40/",
                    "log_home": "/opt/arris/servassure/log"
                },
                "log_pattern": ["reactor.*"],
                "metrics": ["pidstat", "jstat-gc"],
                "clocks": 6
            },

            {
                "name": "SAPM.Reactor@Solaris",
                "type": "java",
                "lookup_keyword": "-Dreactor.home=/export",
                "env" : {
                    "java_home": "/export/home/stargus/jdk1.8.0_40",
                    "log_home": "/export/home/stargus/log/"
                },
                "log_pattern": ["reactor.*"],
                "metrics": ["pidstat", "jstat-gc"],
                "clocks": 6
            },

            {
                "name": "SAPM.Collector@Linux",
                "type": "java",
                "lookup_keyword": "/opt/arris/servassure/jdk1.8.0_40/bin/java -Dprocess=Collector",
                "env" : {
                    "java_home": "/opt/arris/servassure/jdk1.8.0_40/",
                    "log_home": "/opt/arris/servassure/log"
                },
                "log_pattern": ["collection_manager.log", "snmp_poller.log"],
                "metrics": ["pidstat", "jstat-gc"],
                "clocks": 6
            },

            {
                "name": "SAPM.Collector@Solaris",
                "type": "java",
                "lookup_keyword": "/export/home/stargus/jdk1.8.0_40/bin/java -Dprocess=Collector",
                "env" : {
                    "java_home": "/export/home/stargus/jdk1.8.0_40",
                    "log_home": "/export/home/stargus/log/"
                },
                "log_pattern": ["collection_manager.log", "snmp_poller.log"],
                "metrics": ["pidstat", "jstat-gc"],
                "clocks": 6
            },

            {
                "name": "SAPM.Controller@Linux",
                "type": "java",
                "lookup_keyword": "/opt/arris/servassure/jboss/bin/run.jar",
                "env" : {
                    "java_home": "/opt/arris/servassure/jdk1.6.0_30",
                    "log_home": "/opt/arris/servassure/log"
                },
                "log_pattern": ["jboss-*.log"],
                "metrics": ["pidstat", "jstat-gc"],
                "clocks": 6
            },

            {
                "name": "SAPM.Controller@Solaris",
                "type": "java",
                "lookup_keyword": "/export/home/stargus/jboss/bin/run.jar",
                "env" : {
                    "java_home": "/export/home/stargus/jdk1.6.0_30",
                    "log_home": "/export/home/stargus/log/"
                },
                "log_pattern": ["jboss_*.log"],
                "metrics": ["pidstat", "jstat-gc"],
                "clocks": 6
            },

            {
                "name": "SAPM.NodeReceiver@Linux",
                "type": "java",
                "lookup_keyword": "/opt/arris/servassure/node-receiver/conf/receiver.properties",
                "env" : {
                    "java_home": "/opt/arris/servassure/jdk1.6.0_30",
                    "log_home": "/opt/arris/servassure/log"
                },
                "log_pattern": ["jboss-*.log"],
                "metrics": ["pidstat", "jstat-gc"],
                "clocks": 6
            },

            {
                "name": "SAPM.NodeReceiver@Solaris",
                "type": "java",
                "lookup_keyword": "/export/home/stargus/node-receiver/conf/receiver.properties",
                "env" : {
                    "java_home": "/export/home/stargus/jdk1.6.0_30",
                    "log_home": "/export/home/stargus/log/"
                },
                "log_pattern": ["jboss_*.log"],
                "metrics": ["pidstat", "jstat-gc"],
                "clocks": 6
            }
        ]
    }

    def __init__(self):
        config = self.CONFIG
        self._node_metrics = config.get('node_metrics', {})
        self._valid_node_metrics = None
        self._service_metrics = config.get('service_metrics', {})
        self._services = config.get('services',[])
        self._valid_services = None
        self._validate()

        # clocks
        self._clock_interval = config.get('clock_interval', 10)
        self._hb_clocks = config.get('heartbeat_clocks', 60)

    def _validate(self):
        # check node metrics
        logging.info('check node metric commands')
        self._valid_node_metrics = dict((k, v) for k, v in self._node_metrics.items()
                                        if is_valid_exist(v['cmd'][0]))
        logging.info('valid node metrics = %s', self._valid_node_metrics)

        # check services
        invalid_serivces = [s for s in self._services if 'name' not in s or 'lookup_keyword' not in s]
        if invalid_serivces:
            self._valid_services = [s for s in self._services if s not in invalid_serivces]
        else:
             self._valid_services = self._services
        logging.info('valid service=%s, invalid services=%s',
                     map(lambda x: x['name'], self._valid_services),
                     map(lambda x: x['name'], invalid_serivces))

    @property
    def node_metrics(self):
        return self._node_metrics

    @property
    def valid_node_metrics(self):
        return self._valid_node_metrics

    @property
    def service_metrics(self):
        return self._service_metrics

    @property
    def valid_services(self):
        return self._valid_services

    @property
    def clock_interval(self):
        return self._clock_interval

    @property
    def hb_clocks(self):
        return self._hb_clocks


class NodeCollector(threading.Thread):

    CMD_VAR_PATTERN = re.compile('\${([\w_]+)}')

    def __init__(self, agent, config):
        super(NodeCollector, self).__init__(target=self._collect, name='NodeCollector')
        self._agent = agent
        self._agentid = agent.agentid
        self._delay = threading.Event()
        self._config = config
        self.setDaemon(True)

    def _collect(self):
        interval = self._config.clock_interval
        loops = 1;
        while True:
            self._delay.wait(interval)
            time1 = datetime.now()
            try:
                try:
                    if loops % self._config.hb_clocks == 0:
                        self._prod_heartbeat()
                    self._collect_nmetrics(loops)
                    self._collect_smetrics(loops)
                except Exception:
                    logging.exception('error during collect metrics, wait for next round.')
            finally:
                loops = loops + 1
                time2 = datetime.now()
                time_used = (time2 - time1).seconds
                interval = self._config.clock_interval - time_used

    def _prod_heartbeat(self):
        logging.info('produce heartbeat...')
        body = {'datetime': datetime.now()}
        hb_msg = Msg.create_msg(self._agentid, Msg.A_HEARTBEAT, body)
        self._agent.add_msg(hb_msg)

    def _translate_cmd(self, cmd, context={}):
        logging.debug('translate cmd=%s by context=%s', cmd, context)
        newcmd = []
        for c in cmd:
            m = self.CMD_VAR_PATTERN.search(c)
            if m:
                var = m.group(1)
                value = context.get(var, None)
                if value is not None:
                    c = c.replace('${%s}' % var, value)
            newcmd.append(c)
        return newcmd

    def _get_cmd_result(self, cmd):
        """
        Execute cmd on local OS and return output of cmd
        :param cmd:
        :return: result string
        """
        result = 'NOT COLLECTED'
        try:
            output = check_output(cmd)
            result = output
        except Exception:
            logging.exception('call cmd %s failed', cmd)
            result = 'call cmd %s failed.' % cmd
        return result

    def _collect_nmetrics(self, loops):
        """
        Collect node metrics
        :param loops: current loops
        """
        logging.info('try to collecting node metrics, loops=%d', loops)
        nmetrics_result = {}
        for k, v in self._config.valid_node_metrics.items():
            if loops % v.get('clocks', 6) == 0:
                nmetrics_result[k] = self._get_cmd_result(v['cmd'])
        if nmetrics_result:
            msg = Msg.create_msg(self._agentid, Msg.A_NODE_METRIC, nmetrics_result)
            msg.set_header(msg.H_COLLECT_AT, datetime.now())
            self._agent.add_msg(msg)
            logging.info('%d node metrics collected', len(nmetrics_result))
        else:
            logging.info('no metric collected ')

    def _collect_smetrics(self, loops):
        """Collect services metrics"""
        services = self._config.valid_services
        logging.info('try to collect services metrics, loops=%s.', loops)
        for service in services:
            clocks = service['clocks']
            if loops % clocks == 0:
                self._collect_service(service)

    def _collect_service(self, service):
        """
        Collect defined metrics from service
        :param service:  service info
        :return: collected result in dict
        """
        logging.debug('collect service : %s', service)

        name = service['name']
        stype = service.get('type', None)
        lookup = service['lookup_keyword']
        pid = self._find_service_pid(name, lookup)
        if not pid:
            logging.warn('can\'t find pid for %s, exit collection.', name)
            return
        metric_names = service['metrics']
        clocks = service['clocks']
        env = service.get('env', {})
        env['pid'] = pid
        logging.info('collecting for service %s(%s): metrics=%s, clocks=%s.',
                     name, pid, metric_names, clocks)
        service_result = {'name': name, 'pid': pid, 'type': stype}
        service_metrics = {}
        for mname in metric_names:
            try:
                metric = self._config.service_metrics[mname]
                cmd = self._translate_cmd(metric['cmd'], env)
                if not is_valid_exist(cmd[0]):
                    logging.debug('cmd %s is not a valid command', cmd[0])
                    continue
                service_metrics[mname] = self._get_cmd_result(cmd)
            except Exception:
                logging.exception('collect metrics %s for service %s failed: cmd=%s', mname, name, cmd)
        service_result['metrics'] = service_metrics
        if service_metrics:
            # send message
            msg = Msg.create_msg(self._agentid, Msg.A_SERVICE_METRIC, service_result)
            msg.set_header(Msg.H_COLLECT_AT, datetime.now())
            self._agent.add_msg(msg)
            logging.info('%d metrics collected for %s.', len(service_metrics), name)
        else:
            logging.info('no metrics collected for %s', name)
        return service_result

    def _find_service_pid(self, servname, lookup_keyword):
        """
        find the pid of service by keyword, via `ps -ef`
        :param servname:
        :param lookup_keyword:
        :return: pid or None if not found
        """
        service_pid = None
        logging.info('lookup pid service=%s, keyworkd=%s', servname, lookup_keyword)
        try:
            pslist = check_output(['ps', '-ef'])
            psinfo = [psinfo for psinfo in pslist.split('\n') if lookup_keyword in psinfo]
            logging.debug('find psinfo of %s: %s', servname, psinfo)
            if len(psinfo) == 1:
                pid = [e for e in psinfo[0].split(' ') if e][1]
                if pid and pid.isdigit():
                    service_pid = pid
                else:
                    service_pid = None
            logging.info('pid of service %s is %s', servname, service_pid)
        except Exception:
            logging.exception('look up service %s by %s failed', servname, lookup_keyword)
        return service_pid


class NodeAgent:
    """Agent will running the node as and keep send stats data to Master via TCP connection."""
    SEND_BUF = 128*1024

    def __init__(self, master_host='localhost', master_port=7890):
        logging.info('init agent...')
        self._hostname = socket.gethostname()
        self._agentid = self._gen_agentid()
        self._master_addr = (master_host, master_port)
        self._started = False
        self._queue = Q.Queue(maxsize=16)
        self._retry = threading.Event()
        self._config = AgentConfig()
        self._stat_collector = NodeCollector(self, self._config)
        logging.info('agent init with id=%s, master=%s, hostname=%s',
                     self._agentid, self._master_addr, self._hostname)

    @property
    def agentid(self):
        return self._agentid

    def _gen_agentid(self):
        aid = None
        if ostype() == OSType.WIN:
            if len(self._hostname) >= 8:
                aid = self._hostname[0:8]
            else:
                aid = self._hostname.ljust(8, 'x')
        else:
            hostid = check_output(['hostid'])
            if len(hostid) >= 8:
                aid = hostid[0:8]
            else:
                aid = hostid.ljust(8, 'x')
        return aid

    def _connect_master(self):
        if getattr(self, 'sock', None):
            logging.warn('Found exiting socket, now close it.')
            try:
                self.sock.close()
            except socket.error:
                pass

        logging.info('connecting master %s', self._master_addr)
        tried = 0
        while 1:
            tried = tried + 1
            try:
                sock = socket.socket()
                sock.connect(self._master_addr)
                sock.setblocking(False)
                sendbuf =  sock.getsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF)
                logging.info('default send buffer is %s, will change to %s.', sendbuf, self.SEND_BUF)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 1024*128)
                break
            except socket.error:
                sleeptime = min(_MAX_BACKOFF_SECOND, tried ** 2)
                logging.exception('Cannot connect %s(tried=%d), retry after %d seconds...',
                                  self._master_addr, tried, sleeptime)
                self._retry.wait(sleeptime)
        logging.info('connect master(%s) succed.', self._master_addr)
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
                if self._queue.full():
                    oldest_msg = self._queue.get_nowait()
                    logging.debug('q is full, msg %s abandoned, qsize=%d.',
                                  oldest_msg, self._queue.qsize())
                self._queue.put_nowait(msg)
                logging.info('msg %s added to queue, retry=%d, qsize=%d.', msg, retry, self._queue.qsize())
                break;
            except Q.Full:
                # Queue is full, retry
                retry += 1

    def _do_reg(self):
        """Produce a agent reg message after connected"""
        logging.info('do registration...')
        reg_data = {'os': os.name, 'hostname': self._hostname}
        reg_msg = Msg.create_msg(self._agentid, Msg.A_REG, reg_data)
        self.add_msg(reg_msg)

    def _loop(self):
        logging.info('start agent looping...')
        while self._started:
            rlist = elist = [self.sock]
            wlist = []
            if not self._queue.empty():
                wlist = [self.sock]
            try:
                # wait for 5 seconds in each loop to avoid cpu consuming
                rlist, wlist, elist = select.select(rlist, wlist, wlist, 5)
                if rlist:
                    self._do_read(rlist[0])
                if wlist:
                    self._do_write(wlist[0])
                if elist:
                    self._do_error(elist[0])
            except socket.error:
                logging.exception('error in loop.')
                self._connect_master()
            except InvalidMsgError:
                logging.error('invalid message received.')
                self.stop()

    def _do_read(self, sock):
        rdata = sock.recv(1024)
        if not rdata:
            raise InvalidMsgError('get invalid msg ' + rdata + ' from master')
        else:
            logging.info('get data %s from master', rdata.strip())

    def _do_write(self, sock):
        while not self._queue.empty():
            try:
                msg = self._queue.get_nowait()
            except Q.Empty:
                logging.warn('Try to get msg from empty queue..')
                return
            msg.set_header(msg.H_SEND_AT, datetime.now())
            headers, body = msg.encode()
            headers.append(body)
            data = '\n'.join(headers)
            datasize = len(data)
            self._send_data(sock, 'MSG:%d\n' % datasize)
            times = self._send_data(sock, data)
            logging.info('send msg type=%s, datasize=%d, times=%d to=%s',
                          msg.msg_type, datasize, times, self._master_addr)

    def _send_data(self, sock, data):
        times = 0
        while data:
            try:
                try:
                    sent = sock.send(data)
                    data = data[sent:]
                except socket.error:
                    logging.exception('send data failed by times = %d', times)
                    continue
            finally:
                times += 1
        return times

    def _do_error(self, sock):
        logging.info('error happens for %s', sock)


if __name__ == '__main__':

    try:
        opts, args = getopt.getopt(sys.argv[1:], 'p:')
    except getopt.GetoptError:
        print('Wrong usage')
        sys.exit(2)
    mhost = 'localhost'
    if len(args) == 1:
        mhost = args[0]
    port = 7890
    for opt, v in opts:
        if opt in ['-p', '--port']:
            port = v

    agent = NodeAgent(mhost, port)
    agent.start()