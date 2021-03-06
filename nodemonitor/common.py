#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Created on 2017-12-22
@author: foxty

Common for node monitor
"""
# ==============================
#   Common Area (Agent & Master)
# ==============================
import sys
import os
import re
import logging
try:
    import json, json.decoder
except:
    pass
import logging.handlers
import pickle
import socket
from subprocess import Popen, PIPE
from base64 import standard_b64encode, standard_b64decode
from datetime import datetime, date, time
from struct import *

LOGGING_FMT = '%(asctime)s %(levelname)s %(process)d[%(threadName)s]:%(name)s:%(module)s[%(lineno)d]: %(message)s'
DATETIME_FMT = '%Y-%m-%dT%H:%M:%SZ'
DATETIME_RE = re.compile('^\\d{4}-\\d{1,2}-\\d{1,2}T\\d{2}:\\d{2}:\\d{2}Z$')
DATE_FMT = '%Y-%m-%d'
DATE_RE = re.compile('^\\d{4}-\\d{1,2}-\\d{1,2}$')
TIME_FMT = '%H:%M:%S'
TIME_RE = re.compile('^\\d{2}:\\d{2}:\\d{2}$')


def set_logging(filename, when='d', backupCount=7):
    logging.basicConfig(level=logging.INFO,
                        datefmt=DATETIME_FMT,
                        format=LOGGING_FMT)
    trh = logging.handlers.TimedRotatingFileHandler(filename, when=when, backupCount=backupCount)
    trh.setLevel(logging.INFO)
    trh.setFormatter(logging.Formatter(fmt=LOGGING_FMT, datefmt=DATETIME_FMT))
    logging.root.addHandler(trh)


VAR_PATTERN = re.compile('\${([\w_:-]+)}')


def interpret_exp(content, context={}):
    if not isinstance(content, basestring):
        return content
    logging.debug('interpret content=%s by context=%s', content, context)
    keys = VAR_PATTERN.findall(content)
    for key in keys:
        if ':' in key:
            k, d = key.split(':')
        else:
            k, d = key, None
        value = context.get(k, d)
        if value is not None:
            content = content.replace('${%s}' % key, str(value))
    return content


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

    # Message from agnet
    NONE = 'NONE'
    A_REG = 'A_REG'
    A_HEARTBEAT = 'A_HEARTBEAT'
    A_NODE_METRIC = 'A_NODE_METRIC'
    A_SERVICE_METRIC = 'A_SERVICE_METRIC'

    # Message from master
    M_STOP_COLLECT = 'M_STOP_COLLECT'
    M_CONFIG_UPDATE = 'M_CONFIG_UPDATE'

    # Headers definition
    H_AID = 'AgentID'
    H_MSGTYPE = 'MessageType'
    H_CREATE_AT = 'CreateAt'
    H_COLLECT_AT = 'CollectAt'
    H_SEND_AT = 'SendAt'

    SUPPORT_HEADERS = [H_AID, H_MSGTYPE, H_COLLECT_AT, H_SEND_AT]
    SUPPORT_TYPES = [A_REG, A_HEARTBEAT, A_NODE_METRIC, A_SERVICE_METRIC, M_STOP_COLLECT, M_CONFIG_UPDATE]

    def __init__(self, headers=None, body=""):
        self._headers = {}
        if headers:
            self._headers.update(headers)
        self._body = body

    def set_header(self, header, value):
        if header not in self.SUPPORT_HEADERS:
            raise InvalidMsgError('header %s not supported.' % header)
        if header in [self.H_COLLECT_AT, self.H_SEND_AT]:
            value = value.strftime(DATETIME_FMT)
        self._headers[header] = value

    @property
    def agentid(self):
        return self._headers[self.H_AID]

    @property
    def msg_type(self):
        return self._headers[self.H_MSGTYPE]

    @property
    def collect_at(self):
        cat = self._headers.get(self.H_COLLECT_AT, None)
        if cat:
            return datetime.strptime(cat, DATETIME_FMT)
        else:
            return None

    @property
    def send_at(self):
        sat = self._headers.get(self.H_SEND_AT, None)
        if sat:
            return datetime.strptime(sat, DATETIME_FMT)
        else:
            return None

    @property
    def body(self):
        return self._body

    def set_body(self, body):
        self._body = body

    def encode(self):
        """encode msg to list of headers and body content.
        e.g:
        [MSG:A_REG, AgentID:xxxxxxx, SendTime:YYYYMMDD HH:mm:ss], <body>
        """
        head = map(lambda x: '%s:%s' % (x[0], standard_b64encode(x[1])), self._headers.items())
        encbody = standard_b64encode(pickle.dumps(self._body, protocol=pickle.HIGHEST_PROTOCOL))
        return head, encbody

    def __eq__(self, other):
        if isinstance(other, Msg):
            return other.agentid == self.agentid and \
                   other.msg_type == self.msg_type and \
                   other.body == self.body
        else:
            return False

    def __str__(self):
        return '%s[aid=%s]' % (self.msg_type, self.agentid)

    @classmethod
    def decode(cls, header_list=[], body=''):
        headers = dict((h[:h.index(':')], standard_b64decode(h[h.index(':') + 1:])) for h in header_list)
        body = pickle.loads(standard_b64decode(body))
        return Msg(headers=headers, body=body)

    @classmethod
    def create_msg(cls, aid, msgtype, body=''):
        return Msg(headers={Msg.H_AID: aid, Msg.H_MSGTYPE: msgtype}, body=body)


class OSType(object):
    WIN = 'WIN'
    LINUX = 'LINUX'
    SUNOS = 'SUNOS'


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

    def __init__(self, content, header_ln=0, vheader=False, colsep='\s+'):
        self._table = [[ele for ele in re.split(colsep, l.strip()) if ele]
                       for l in content.splitlines() if l.strip()]
        tbl_size = len(self._table)
        self._size = tbl_size - (header_ln + 1)
        if tbl_size > header_ln:
            self._hheader = self._table[header_ln]
        if tbl_size > header_ln + 1:
            self._tbody = self._table[header_ln + 1:]
        if vheader:
            self._vheader = [row[0] for row in self._table]

    def __getitem__(self, item):
        return TextTableRow(self, item)

    @property
    def size(self):
        return self._size

    @property
    def has_body(self):
        return self._size >= 1

    def get_rows(self):
        return [TextTableRow(self, rowno) for rowno, content in enumerate(self._tbody)]

    def gets(self, rowid, header, conv_func=str):
        """get values for header_name in row #rowno,
        :param rowid: row number or row name
        :param header: header name
        :param conv_func: conversion function
        :return: list of values (in case multi columns has same header name)
        """
        if type(rowid) is int:
            rowno = rowid
        else:
            rowno = self._vheader.index(rowid) - 1
        idxs = []
        if type(header) is int:
            idxs.append(header)
        else:
            start = 0
            while True:
                try:
                    idx = self._hheader.index(header, start)
                    idxs.append(idx)
                    start = idx + 1
                except ValueError:
                    break
        return [conv_func(self._tbody[rowno][idx]) for idx in idxs]

    def get(self, rowno, header, default=None, conv_func=str):
        values = self.gets(rowno, header, conv_func=conv_func)
        if values:
            return values[0]
        else:
            return default

    def get_ints(self, rowno, header):
        return self.gets(rowno, header, conv_func=int)

    def get_int(self, rowno, header, default=None):
        return self.get(rowno, header, default, conv_func=int)

    def get_floats(self, rowno, header):
        return self.gets(rowno, header, conv_func=float)

    def get_float(self, rowno, header, default=None):
        return self.get(rowno, header, default, conv_func=float)


class TextTableRow(object):

    def __init__(self, tbl, rowno):
        """
        :param tbl: parent TextTable
        :param rowno: start from 0
        """
        self._parent = tbl
        self._row_index = rowno

    def as_tuple(self):
        return tuple(self._parent._tbody[self._row_index])

    def __getitem__(self, item):
        return self.get(item)

    def gets(self, header, conv_func=str):
        return self._parent.gets(self._row_index, header, conv_func=conv_func);

    def get(self, header, default=None, conv_func=str):
        values = self._parent.gets(self._row_index, header, conv_func=conv_func)
        if values:
            return values[0]
        else:
            return default

    def get_ints(self, header):
        return self._parent.get_ints(self._row_index, header)

    def get_int(self, header, default=None):
        return self._parent.get_int(self._row_index, header, default)

    def get_floats(self, header):
        return self._parent.get_floats(self._row_index, header)

    def get_float(self, header, default=None):
        return self._parent.get_float(self._row_index, header, default)


class YAMLConfig(object):
    LOGGER = logging.getLogger('YAMLConfig')
    EXP_RE = re.compile('\$\{.*\}')

    def __init__(self, url, config=None):
        if config is not None:
            self._url = url
            self._config = config
        else:
            if not os.path.isfile(url):
                raise ConfigError('config file %s not found.', url)
            self._url = url
            self._config = None
            import yaml
            s = open(self._url)
            try:
                self._config = yaml.load(s)
            finally:
                s.close()
            self.LOGGER.info('config %s loaded.', url)

    def __getitem__(self, item):
        v = self._config[item]
        if type(v) in [dict, list]:
            return YAMLConfig(self._url, v)
        else:
            return interpret_exp(v, os.environ)

    def __setitem__(self, key, value):
        raise ConfigError('config is immutable.')

    def __str__(self):
        return self._config.__str__()


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


def process_info(lookup_keyword):
    """
    1, Get all process info by 'ps -ef' and pickup target process by lookup_keywor.
    2, Get (pid, puser, penvs) for finded process/
    :param lookup_keyword:
    :return: (puser, pid, penvs) or (None, None, None) if not found
    """
    puser = None
    pid = None
    penvs = {}
    try:
        pslist = check_output(['ps', '-ef'])
        psinfo = [psinfo for psinfo in pslist.split('\n') if lookup_keyword in psinfo]
        logging.debug('get psinfo %s of "%s"', psinfo, lookup_keyword)
        if len(psinfo) == 1:
            puser, pid = [e.strip() for e in psinfo[0].split(' ') if e][0:2]
            if pid and pid.isdigit() and puser:
                puser = puser
                pid = pid
                penvs = user_envs(puser)
        else:
            logging.info('get %s process(es) by "%s"', len(psinfo), lookup_keyword)
    except Exception:
        logging.exception('look up process by %s failed', lookup_keyword)
    return puser, pid, penvs


def user_envs(user):
    envs = {}
    try:
        out = check_output(['su', '-', user, '-c', 'env'])
        for kv in [line.split('=') for line in out.splitlines() if line.strip()]:
            if len(kv) == 2:
                envs[kv[0].strip()] = kv[1].strip()
    except CalledProcessError:
        logging.exception('get env from user "%s" failed', user)
    return envs


def dump_json(obj):
    """customized json encoder function to support datetime, date, time object"""

    def dt_converter(o):
        if isinstance(o, datetime):
            return o.strftime(DATETIME_FMT)
        elif isinstance(o, date):
            return o.strftime(DATE_FMT)
        elif isinstance(o, time):
            return o.strftime(TIME_FMT)
        else:
            raise TypeError('Object %s not support by JSON encoder', o)

    return json.dumps(obj, default=dt_converter)


def load_json(str):
    """customized json decoder function to support datetime, date, time object"""

    def decode_date(v):
        if isinstance(v, basestring):
            if DATETIME_RE.match(v):
                return datetime.strptime(v, DATETIME_FMT)
            elif DATE_RE.match(v):
                return datetime.strptime(v, DATE_FMT)
            elif TIME_RE.match(v):
                return datetime.strptime(v, TIME_FMT)
            else:
                return v
        else:
            return v

    def obj_hook(dct):
        return dict((k, decode_date(v)) for k, v in dct.items())

    return json.loads(str, object_hook=obj_hook)


def read_msg(sock):
    # read message stamper "MSG:<LENGTH>\n"
    stamper = ''
    while not stamper or stamper[-1] != '\n':
        stamper += sock.recv(1)
    stamper_items = stamper.strip().split(':')
    if len(stamper_items) != 2 or not stamper_items[1].isdigit():
        logging.warn('invalid message stamper %s from %s', stamper, sock.getpeername())
        return
    else:
        length = int(stamper_items[1])
        data = ''
        while len(data) < length:
            try:
                data += sock.recv(length - len(data))
            except socket.error:
                _, e, _ = sys.exc_info()
                if e.errno == 10035:
                    # [Errno 10035] A non-blocking socket operation could not be completed immediately
                    # should be ignored
                    pass
                else:
                    raise e
        if length != len(data):
            logging.warn('invalid message length (%s != %s) from %s', length, len(data), sock.getpeername())
            return
        msgdata = data.split('\n')
        headers, body = msgdata[:-1], msgdata[-1]
        msg = Msg.decode(headers, body)
        logging.debug("recv msg %s from %s", msg, sock.getpeername())
        return msg


def send_msg(sock, msg):
    headers, body = msg.encode()
    data = '\n'.join(headers + [body])
    datasize = len(data)
    bucket = 'MSG:%d\n' % datasize + data
    times = 0
    while bucket:
        try:
            try:
                sent = sock.send(bucket)
                bucket = data[sent:]
            except socket.error:
                logging.exception('send data failed by times = %d', times)
                if times > 10:
                    logging.info('break the send msg loop while times=%s', times)
                    break
        finally:
            times += 1
    return datasize, times