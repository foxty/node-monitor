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
import logging
import re
import socket
import SocketServer
import sqlite3
from datetime import datetime
from uuid import uuid4
from common import Msg, InvalidMsgError, TextTable


# ====================
# const definition
#====================


_MASTER = None
_MASTER_DB_NAME = 'master.db'
_DB_SCHEMA = r'''
    CREATE TABLE IF NOT EXISTS agent(aid UNIQUE, name, host, create_at timestamp, 
        last_msg_at, last_cpu_util, last_mem_util, last_sys_load1, last_sys_cs);
    
    CREATE TABLE IF NOT EXISTS node_metric_raw(aid, collect_at timestamp, category, content, recv_at timestamp);
    CREATE INDEX IF NOT EXISTS `idx_nmr_aid` ON `node_metric_raw` (`aid` DESC);
    CREATE INDEX IF NOT EXISTS `idx_nmr_collect_at` ON `node_metric_raw` (collect_at DESC);
    CREATE INDEX IF NOT EXISTS `idx_nmr_recv_at` ON `node_metric_raw` (recv_at DESC);
    
    CREATE TABLE IF NOT EXISTS node_memory_report(
        aid, collect_at timestamp, total_mem, used_mem, free_mem, cache_mem, 
        total_swap, used_swap, free_swap, recv_at timestamp);
    CREATE INDEX IF NOT EXISTS `idx_nmre_aid` ON `node_memory_report` (`aid` DESC);
    CREATE INDEX IF NOT EXISTS `idx_nmre_collect_at` ON `node_memory_report` (collect_at DESC);
    CREATE INDEX IF NOT EXISTS `idx_nmre_recv_at` ON `node_memory_report` (recv_at DESC);
        
    CREATE TABLE IF NOT EXISTS node_cpu_report(aid, collect_at timestamp, us, sy, id, wa, st, recv_at timestamp);
    CREATE INDEX IF NOT EXISTS `idx_ncr_aid` ON `node_cpu_report` (`aid` DESC);
    CREATE INDEX IF NOT EXISTS `idx_ncr_collect_at` ON `node_cpu_report` (collect_at DESC);
    CREATE INDEX IF NOT EXISTS `idx_ncr_recv_at` ON `node_cpu_report` (recv_at DESC);
    
    CREATE TABLE IF NOT EXISTS node_system_report(aid, collect_at timestamp, uptime, users, 
        load1, load5, load15, procs_r, procs_b, sys_in, sys_cs, recv_at timestamp);
    CREATE INDEX IF NOT EXISTS idx_nsr_aid ON node_system_report (aid DESC);
    CREATE INDEX IF NOT EXISTS idx_nsr_collect_at ON node_system_report (collect_at DESC);
    CREATE INDEX IF NOT EXISTS idx_nsr_recv_at ON node_system_report (recv_at DESC);
    
    CREATE TABLE IF NOT EXISTS node_disk_report(aid, collect_at timestamp, fs, size, used, 
        available, used_util, mount_point, recv_at timestamp);
    CREATE INDEX IF NOT EXISTS idx_ndr_aid ON node_disk_report (aid DESC);
    CREATE INDEX IF NOT EXISTS idx_ndr_collect_at ON node_disk_report (collect_at DESC);
    CREATE INDEX IF NOT EXISTS idx_ndr_recv_at ON node_disk_report (recv_at DESC);
    
    CREATE TABLE IF NOT EXISTS service_metric_raw(aid, collect_at timestamp, name, pid, 
        category, content, recv_at timestamp);
    CREATE INDEX IF NOT EXISTS `idx_nsr_aid` ON `service_metric_raw` (`aid` DESC);
    CREATE INDEX IF NOT EXISTS `idx_nsr_collect_at` ON `service_metric_raw` (collect_at DESC);
    CREATE INDEX IF NOT EXISTS `idx_nsr_recv_at` ON `service_metric_raw` (recv_at DESC);
    
    CREATE TABLE IF NOT EXISTS service(id PRIMARY KEY NOT NULL, aid, name, pid, type, last_report_at timestamp, status);
    CREATE INDEX IF NOT EXISTS `idx_si_aid` ON `service` (aid);
    CREATE INDEX IF NOT EXISTS `idx_si_report_at` ON `service` (last_report_at DESC);
    
    CREATE TABLE IF NOT EXISTS service_history(service_id, pid, change_at timestamp);
    
    CREATE TABLE IF NOT EXISTS service_pidstat_report(aid, service_id, collect_at timestamp, 
        tid, cpu_us, cpu_sy, cpu_gu, cpu_util, mem_minflt, mem_majflt, mem_vsz, mem_rss, mem_util,
        disk_rd, disk_wr, disk_ccwr, recv_at timestamp);
    CREATE INDEX IF NOT EXISTS `idx_spr_aid` ON `service_pidstat_report` (`aid` DESC);
    CREATE INDEX IF NOT EXISTS `idx_spr_collect_at` ON `service_pidstat_report` (collect_at DESC);
    CREATE INDEX IF NOT EXISTS `idx_spr_recv_at` ON `service_pidstat_report` (recv_at DESC);
    
    CREATE TABLE IF NOT EXISTS service_jstatgc_report(aid, service_id, collect_at timestamp, 
        ts, s0c, s1c, s0u, s1u, ec, eu, oc, ou, mc, mu, ccsc, ccsu, ygc, ygct, fgc, fgct, gct, recv_at timestamp);
    CREATE INDEX IF NOT EXISTS `idx_sjgc_aid` ON `service_jstatgc_report` (`aid` DESC);
    CREATE INDEX IF NOT EXISTS `idx_sjgc_collect_at` ON `service_jstatgc_report` (collect_at DESC);
    CREATE INDEX IF NOT EXISTS `idx_sjgc_recv_at` ON `service_jstatgc_report` (recv_at DESC);
    
    CREATE TABLE IF NOT EXISTS alarm(id PRIMARY KEY, entity_id, entity_type, type, state, duration, create_at timestamp);
    '''
_RE_SYSREPORT = re.compile('.*?(?P<users>\\d+)\\suser.*'
                           'age: (?P<load1>\\d+\\.\\d+), (?P<load5>\\d+\\.\\d+), (?P<load15>\\d+\\.\\d+).*',
                           re.S)


# ====================
# Global functions
# ====================


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


@dao
def create_schema(cursor):
    logging.info('init master db with schema %s', _DB_SCHEMA)
    cursor.executescript(_DB_SCHEMA)


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
        days = 0
        users = int(m.group('users'))
        load1 = float(m.group('load1'))
        load5 = float(m.group('load5'))
        load15 = float(m.group('load15'))
        return NSystemReport(aid, collect_time, uptime=days*24*3600, users=users,
                             load1=load1, load5=load5, load15=load15,
                             procs_r=None, procs_b=None, sys_in=None, sys_cs=None
                             , recv_at=datetime.now())
    else:
        logging.warn('invalid content of `w`: %s', content)
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
                             used_swap=use_swap, free_swap=free_swap, recv_at=datetime.now())
    else:
        logging.warn('invalid content of`free`: %s', content)
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
    if t.size == 2:
        data_rn = -1
        procs_r, procs_b = t.get_int(data_rn,'r'), t.get_int(data_rn,'b')
        sys_in, sys_cs = t.get_int(data_rn,'in'), t.get_int(data_rn,'cs')
        us, sy = t.get_int(data_rn,'us'), t.get_ints(data_rn,'sy')[-1]
        id_, wa = t.get_int(data_rn,'id'), t.get_int(data_rn,'wa')
        st = t.get_int(data_rn,'st')
        r = NCPUReport(aid=aid, collect_at=collect_time,
                       us=us, sy=sy,id=id_, wa=wa, st=st, recv_at=datetime.now())
        return r, procs_r, procs_b, sys_in, sys_cs
    else:
        logging.warn('invalid content of `vmstat` : %s', content)
        return None, None, None, None, None


def parse_df(aid, collect_time, content):
    """
    Parse the output of df command get disk utilization data
    :param aid: agentid
    :param collect_time: local time in node
    :param content: output of command `df -k`
    :return: list of disk utilization record
    """
    t = TextTable(content)
    if t.size > 1:
        diskreps = [NDiskReport(aid, collect_time, *row.as_tuple(), recv_at=datetime.now()) for row in t.get_rows()]
        return diskreps
    else:
        logging.warn('invalid content of `df` : %s', content)
        return None


def parse_netstat(aid, collect_time, content):
    pass


def parse_dstat(content, data_size):
    """ parse the output of dstat command and get last line of data.
    :param content:
    :param data_size:
    :return: List[str] for data and None if invalid content
    """
    if content:
        data = re.split('\s*\|?\s*', [l.strip() for l in content.splitlines() if l.strip()][-1])
        return data if len(data) == data_size else None
    logging.warn('invalid content for dstat %s', content)
    return None


def parse_dstat_sys(aid, collect_time, content):
    """ parse the output of `dstat -lyp` to NSystemReport
     ---load-avg--- ---system-- ---procs---
     1m   5m  15m | int   csw |run blk new
     0 0.02    0| 401   750 |  0   0 0.4
     0 0.02    0| 223   501 |  0   0   0
    :param aid:
    :param collect_time:
    :param content:
    :return: NSystemReport
    """
    data = parse_dstat(content, 8)
    return NSystemReport(aid=aid, collect_at=collect_time,
                         load1=float(data[0]), load5=float(data[1]), load15=float(data[2]),
                         sys_in=int(data[3]), sys_cs=int(data[4]), procs_r=int(data[5]),
                         procs_b=int(data[6]), recv_at=datetime.now()) if data else None


def parse_dstat_cpu(aid, collect_time, content):
    """ parse the output of `dstat -c` to NCPUReport
     ----total-cpu-usage----
     usr sys idl wai hiq siq
     0   0  99   1   0   0
     0   0 100   0   0   0
    :param aid:
    :param collect_time:
    :param content:
    :return: NCPUReport
    """
    data = parse_dstat(content, 6)
    return NCPUReport(aid=aid, collect_at=collect_time, us=int(data[0]), sy=int(data[1]),
                         id=int(data[2]), wa=int(data[3]), recv_at=datetime.now()) if data else None


def conv_to_mega(value, multiplier=1024):
    if value[-1] in ('G', "g"):
        return float(value[:-1]) * multiplier
    elif value[-1] in ('M', 'm'):
        return float(value[:-1])
    elif value[-1] in ('K', 'k'):
        return float(value[:-1]) / multiplier
    elif value[-1] in ('B', 'b'):
        return float(value[:-1]) / (multiplier ** 2)
    elif value.isdigit():
        return float(value)
    else:
        return None


def parse_dstat_mem(aid, collect_time, content):
    """
    ------memory-usage----- ----swap--- ---paging--
    used  buff  cach  free| used  free|  in   out
    3666M  197M 9.80G 6096M|   0    10G|   0     0
    3666M  197M 9.80G 6096M|   0    10G|   0     0
    :param aid:
    :param collect_time:
    :param content:
    :return: NMemoryReport
    """
    data = parse_dstat(content, 8)
    if data:
        used_mem = conv_to_mega(data[0])
        cache_mem = conv_to_mega(data[2])
        free_mem = conv_to_mega(data[3])
        used_swap = conv_to_mega(data[4])
        free_swap = conv_to_mega(data[5])
        page_in, page_out = int(data[6]), int(data[7])
    return NMemoryReport(aid, collect_time, total_mem=used_mem+cache_mem+free_mem,
                         used_mem=used_mem, free_mem=free_mem, cache_mem=cache_mem,
                         total_swap=used_swap+free_swap, used_swap=used_swap,
                         free_swap=free_swap, recv_at=datetime.now()) if data else None


def parse_dstat_sock(aid, collect_time, content):
    pass


def parse_dstat_dio(aid, collect_time, content):
    pass


def parse_pidstat(aid, collect_time, service_id, content):
    t = TextTable(content, header_ln=1)
    if t.size > 1:
        prow = t[0]
        tid = int(prow[2])
        cpu_us, cpu_sy, cpu_gu, cpu_util = float(prow[3]), float(prow[4]), float(prow[5]), float(prow[6])
        mem_minflt, mem_majflt, mem_vsz, mem_rss, mem_util = float(prow[8]), float(prow[9]), \
                                                             int(prow[10]), int(prow[11]), float(prow[12])
        disk_rd, disk_wr, disk_ccwr = float(prow[13]), float(prow[14]), float(prow[15])
        rep = SPidstatReport(aid=aid, service_id=service_id, collect_at=collect_time, tid=tid,
                             cpu_us=cpu_us, cpu_sy=cpu_sy, cpu_gu=cpu_gu, cpu_util=cpu_util,
                             mem_minflt=mem_minflt, mem_majflt=mem_majflt, mem_vsz=mem_vsz, mem_rss=mem_rss, mem_util=mem_util,
                             disk_rd=disk_rd, disk_wr=disk_wr, disk_ccwr=disk_ccwr, recv_at=datetime.now())
        logging.debug('get pidsat report %s', rep)
        return rep
    else:
        logging.warn('invalid content of `pidstat` : %s', content)
        return None


def parse_jstatgc(aid, collect_time, service_id, content):
    t = TextTable(content)
    if t.has_body:
        data = t[0]
        ts = data.get_float('Timestamp')
        S0C, S1C = data.get_float('S0C'), data.get_float('S1C')
        S0U, S1U = data.get_float('S0U'), data.get_float('S1U')
        EC, EU = data.get_float('EC'), data.get_float('EU')
        OC, OU = data.get_float('OC'), data.get_float('OU')
        MC, MU = data.get_float('MC'), data.get_float('MU')
        CCSC, CCSU = data.get_float('CCSC'), data.get_float('CCSU')
        YGC, YGCT = data.get_int('YGC'), data.get_float('YGCT')
        FGC, FGCT, GCT = data.get_int('FGC'), data.get_float('FGCT'), data.get_float('GCT')
        rep = SJstatGCReport(aid=aid, service_id=service_id, collect_at=collect_time, ts=ts,
                             s0c=S0C, s1c=S1C, s0u=S0U, s1u=S1U,
                             ec=EC, eu=EU, oc=OC, ou=OU,
                             mc=MC, mu=MU, ccsc=CCSC, ccsu=CCSU,
                             ygc=YGC, ygct=YGCT, fgc=FGC, fgct=FGCT, gct=GCT, recv_at=datetime.now())
        logging.debug('get jstatgc report %s', rep)
        return rep
    else:
        logging.warn('invalid content of `jstat-gc` : %s', content)
        return None


class InvalidFieldError(Exception): pass


class NoPKError(Exception): pass


# ====================
# Models
# ====================


class Model(dict):
    _TABLE = 'model'
    _FIELDS = []
    _PK = ["_id"]
    _ISQL = None

    def __init__(self, *args, **kwargs):
        upd = None
        if args:
            upd = zip(self._FIELDS[:len(args)], args)
        kwupd = self._check_updates(kwargs)
        upd = kwupd if not upd else upd + kwupd
        if upd:
            self.update({k: v for k, v in upd if v is not None})

    def __getattr__(self, item):
        if item in self._FIELDS:
            return self.get(item, None)
        else:
            raise InvalidFieldError('model field "%s" not defined.' % item)

    def __setattr__(self, key, value):
        if key in self._FIELDS:
            self[key] = value
        else:
            raise InvalidFieldError('field %s not defined.' % key)

    def _check_updates(self, kwargs):
        if kwargs:
            diff = kwargs.viewkeys() - set(self._FIELDS)
            if diff:
                raise InvalidFieldError(','.join(diff))
            else:
                upd = kwargs.items()
        else:
            upd = []
        return upd

    def as_tuple(self):
        return tuple(self.get(f, None) for f in self._FIELDS)

    @dao
    def save(self, cursor):
        """
        save current model to db (INSERT TO)
        :param cursor:
        :return:
        """
        logging.debug('saving model %s to db', self)
        r = cursor.execute(self.isql(), self.as_tuple())
        return self

    @dao
    def set(self, **kwargs):
        """
        update the model and save to db
        :param kwargs:
        :return:
        """
        if not self._PK:
            raise NoPKError(self._TABLE)
        logging.debug('update model %s with %s', self._TABLE, kwargs)
        cursor = kwargs['cursor']
        del kwargs['cursor']
        kwupd = self._check_updates(kwargs)
        if kwupd:
            # clever
            fields, values = zip(*kwupd)
            setphrase = ','.join(['%s=?' % f for f in fields])
            wherephrase = ' AND '.join(['%s=?' % pk for pk in self._PK])
            pkvalues = tuple([self.get(pk) for pk in self._PK])
            sql = 'UPDATE %s SET %s WHERE %s' % (self._TABLE, setphrase, wherephrase)
            params = values + pkvalues
            logging.debug('%s : %s', sql, params)
            cursor.execute(sql, params)
            self.update(kwargs)

    @classmethod
    def isql(cls):
        if not cls._ISQL:
            cls._ISQL = 'INSERT INTO %s (%s) VALUES(%s)' % (cls._TABLE, ','.join(cls._FIELDS), ','.join('?' * len(cls._FIELDS)))
        return cls._ISQL

    @classmethod
    @dao
    def save_all(cls, l, cursor):
        records = [m.as_tuple() for m in l]
        cursor.executemany(cls.isql(), records)

    @classmethod
    @dao
    def query(cls, where=None, orderby=None, params=None, limit=None, offset=None, cursor=None):
        """
        query model list
        :param where: SQL where clause
        :param orderby: SQL order by clause
        :param params: parameters used in where clause
        :param limit: limit numbers of query
        :param offset: offset position of query
        :param cursor: cursor object of database
        :return: lis to of model
        """
        sql = 'SELECT %s FROM %s %s %s %s %s' % (','.join(cls._FIELDS),
                                                 cls._TABLE,
                                                 'WHERE %s' % where if where else '',
                                                 'ORDER BY %s' % orderby if orderby else '',
                                                 'LIMIT %d' % limit if limit is not None else '',
                                                 'OFFSET %d' % offset if offset is not None else '')
        logging.debug('%s : %s', sql, params)
        cursor.execute(sql, params if params else [])
        result = cursor.fetchall()
        return [cls(*r) for r in result]

    @classmethod
    @dao
    def count(cls, where=None, params=None, cursor=None):
        cursor.execute('SELECT COUNT(1) FROM %s %s' % (cls._TABLE, 'WHERE ' + where if where else ''),
                       params if params else ())
        r = cursor.fetchone()
        return r[0] if r else 0


class AgentChronoModel(object):

    @classmethod
    def query_by_ctime(cls, aid, start, end):
        return cls.query(where='aid=? AND collect_at >= ? AND collect_at <= ?', params=[aid, start, end])

    @classmethod
    def query_by_rtime(cls, aid, start, end):
        return cls.query(where='aid=? AND recv_at >= ? AND recv_at <= ?', params=[aid, start, end])


class ServiceChronoModel(object):

    @classmethod
    def query_by_ctime(cls, sid, start, end):
        return cls.query(where='service_id=? AND collect_at >= ? AND collect_at <= ?', orderby='collect_at ASC', params=[sid, start, end])

    @classmethod
    def query_by_rtime(cls, sid, start, end):
        return cls.query(where='service_id=? AND recv_at >= ? AND recv_at <= ?', orderby='collect_at ASC',params=[sid, start, end])


class Agent(Model):
    _TABLE = 'agent'
    _FIELDS = ['aid', 'name', 'host', 'create_at', 'last_msg_at',
              'last_cpu_util', 'last_mem_util', 'last_sys_load1', 'last_sys_cs']
    _PK = ['aid']

    @classmethod
    def get_by_id(cls, aid):
        r = cls.query(where='aid=?', params=[aid])
        return r[0] if r else None

    @classmethod
    def query_by_load1(cls, count=10):
        return cls.query(orderby='last_sys_load1 DESC LIMIT ?', params=[count])


class NMetric(Model, AgentChronoModel):
    _TABLE = 'node_metric_raw'
    _FIELDS = ['aid', 'collect_at', 'category', 'content', 'recv_at']


class NMemoryReport(Model, AgentChronoModel):
    _TABLE = 'node_memory_report'
    _FIELDS = ['aid', 'collect_at', 'total_mem', 'used_mem', 'free_mem',
              'cache_mem', 'total_swap', 'used_swap', 'free_swap', 'recv_at']

    @property
    def used_util(self):
        return self.used_mem*100/self.total_mem if self.used_mem and self.total_mem else None

    @property
    def free_util(self):
        return self.free_mem*100/self.total_mem if self.free_mem and self.total_mem else None


class NCPUReport(Model, AgentChronoModel):
    _TABLE = 'node_cpu_report'
    _FIELDS = ['aid', 'collect_at', 'us', 'sy', 'id', 'wa', 'st', 'recv_at']

    @property
    def used_util(self):
        return self.us + self.sy if self.us is not None and self.sy is not None else None


class NSystemReport(Model, AgentChronoModel):
    _TABLE = 'node_system_report'
    _FIELDS = ['aid', 'collect_at', 'uptime', 'users', 'load1', 'load5',
              'load15', 'procs_r', 'procs_b', 'sys_in', 'sys_cs', 'recv_at']


class NDiskReport(Model, AgentChronoModel):
    _TABLE = 'node_disk_report'
    _FIELDS = ['aid', 'collect_at', 'fs', 'size', 'used',
              'available', 'used_util', 'mount_point', 'recv_at']


class SMetric(Model, AgentChronoModel):
    _TABLE = 'service_metric_raw'
    _FIELDS = ['aid', 'collect_at', 'name', 'pid',
              'category', 'content', 'recv_at']


class SInfo(Model):
    _TABLE = 'service'
    _FIELDS = ['id', 'aid', 'name', 'pid', 'type', 'last_report_at', 'status']
    _PK = ['id']

    STATUS_ACT = 'active'
    STATUS_INACT = 'inactive'

    def add_history(self):
        SInfoHistory(service_id=self.id, pid=self.pid, change_at=datetime.now()).save()

    def chgpid(self, newpid):
        self.set(pid=newpid)
        self.add_history()

    def chkstatus(self, threshold_secs):
        active = False
        if self.last_report_at:
            now = datetime.now()
            dt = now - self.last_report_at
            active = dt.seconds <= threshold_secs or self.last_report_at >= now
        self.set(status=self.STATUS_ACT if active else self.STATUS_INACT)
        return active

    @classmethod
    def query_by_aid(cls, aid):
        return cls.query(where='aid=?', orderby='name', params=[aid])


class SInfoHistory(Model):
    _TABLE = 'service_history'
    _FIELDS = ['service_id', 'pid', 'change_at']


class SPidstatReport(Model, ServiceChronoModel):
    _TABLE = 'service_pidstat_report'
    _FIELDS = ['aid', 'service_id', 'collect_at', 'tid', 'cpu_us', 'cpu_sy', 'cpu_gu', 'cpu_util',
              'mem_minflt', 'mem_majflt', 'mem_vsz', 'mem_rss', 'mem_util',
              'disk_rd', 'disk_wr', 'disk_ccwr', 'recv_at']

    @classmethod
    def lst_report_by_aid(cls, aid, count):
        return cls.query(where='aid=?', orderby='collect_at DESC', params=[aid], limit=count)


class SJstatGCReport(Model, ServiceChronoModel):
    _TABLE = 'service_jstatgc_report'
    _FIELDS = ['aid', 'service_id', 'collect_at',
               'ts', 's0c', 's1c', 's0u', 's1u', 'ec', 'eu', 'oc', 'ou', 'mc', 'mu',
               'ccsc', 'ccsu', 'ygc', 'ygct', 'fgc', 'fgct', 'gct', 'recv_at']

    @classmethod
    def lst_report_by_aid(cls, aid, count):
        return cls.query(where='aid=?', orderby='collect_at DESC', params=[aid], limit=count)


class Alarm(Model):
    _TABLE = ""
    _FIELDS = [""]


# =================
# Master
# =================


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


class AgentRequestHandler(SocketServer.StreamRequestHandler):
    """All message are MonMsg and we should decode the msg here"""

    def handle(self):
        self.agentid = None
        try:
            self._loop()
        except Exception as e:
            logging.exception('error while processing data for %s', self.client_address)
        finally:
            if self.agentid:
                status = _MASTER.inactive_agent(self.agentid)
                logging.info('inactive agent %s ', status)
            else:
                logging.info('agent from %s not registered, exit handler.', self.client_address)

    def _chk_msg(self, msg):
        if not _MASTER.find_agent(msg.agentid) and msg.msg_type != Msg.A_REG:
            raise InvalidMsgError('agentid %s not registered from %s' % (msg.agentid, self.client_address))
        elif not self.agentid:
            self.agentid = msg.agentid
            logging.info('new agent %s joined', self.client_address)
        elif self.agentid != msg.agentid:
            raise InvalidMsgError('agentid change detected %d->%d from %s'
                                  % (self.agentid, msg.agentid, self.client_address))

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
            process = _MASTER.handle_msg(msg, self.client_address)
            if not process:
                logging.info('msg handler stopped for %s from %s', msg, self.agentid)


class Master(object):
    """Agent work as the service and received status report from every Agent."""

    def __init__(self, host=socket.gethostname(), port=7890):
        self._addr = (host, port)
        self._agents = None
        self._handlers = {}
        self._server = None
        self._init_handlers()
        self._load_agents()
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
        agents = Agent.query()
        self._agents = {a.aid: a for a in agents}
        logging.info('load %d agents from db', len(agents))

    # Message handlers
    def _agent_reg(self, msg):
        agent = self.find_agent(msg.agentid)
        ahostname = msg.body['hostname']
        if agent:
            agent.set(name=ahostname)
            logging.info('activate existing agent %s', agent)
            # TODO activation
        else:
            agent = Agent(msg.agentid, ahostname, msg.client_addr[0], datetime.now())
            agent.save()
            logging.info('new agent %s registered', agent)
            self._agents[agent.aid] = agent
        return True

    def _agent_heartbeat(self, msg):
        agent = self.find_agent(msg.agentid)
        logging.debug('heart beat get from %s', agent)
        return True

    def _agent_nmetrics(self, msg):
        aid = msg.agentid
        agent = self._agents.get(aid)
        body = msg.body
        collect_time = msg.collect_at

        metrics = map(lambda x: NMetric(aid, collect_time, x[0], x[1], datetime.now()), body.items())
        NMetric.save_all(metrics)

        memrep, cpurep, sysrep = None, None, None

        if 'free' in body:
            memrep = parse_free(aid, collect_time, body['free'])
            memrep.save() if memrep else None
        if 'vmstat' in body:
            cpurep, procs_r, procs_b, sys_in, sys_cs \
                = parse_vmstat(aid, collect_time, body['vmstat'])
            cpurep.save() if cpurep else None
        if 'w' in body:
            sysrep = parse_w(aid, collect_time, body['w'])
            if sysrep:
                sysrep.procs_r = procs_r
                sysrep.procs_b = procs_b
                sysrep.sys_in = sys_in
                sysrep.sys_cs = sys_cs
                sysrep.save()
        if 'df' in body:
            dfreps = parse_df(aid, collect_time, body['df'])
            if dfreps:
                NDiskReport.save_all(dfreps)
        last_cpu_util = cpurep.used_util if cpurep else None
        last_mem_util = memrep.used_util if memrep else None
        last_sys_load1, last_sys_cs = (sysrep.load1, sysrep.sys_cs) if sysrep else (None, None)
        agent.set(last_msg_at=datetime.now(),
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
        smetrics = [SMetric(aid, collect_at, sname, spid, mname, mcontent, datetime.now())
                    for mname, mcontent in body['metrics'].items()]
        SMetric.save_all(smetrics)

        # calculate node services
        services = {s.name: s for s in SInfo.query_by_aid(aid)}
        if sname not in services:
            # service discovered
            logging.info('service %s discovered with pid %s', sname, spid)
            ser = SInfo(id=uuid4().hex, aid=aid, name=sname, pid=spid, type=stype,
                        last_report_at=collect_at, status=SInfo.STATUS_ACT).save()
            ser.add_history()
        else:
            # existing service, check for an update
            logging.debug('refreshing service %s from %s', sname, aid)
            ser = services[sname]
            ser.set(last_report_at=collect_at, status=SInfo.STATUS_ACT)
            if ser.pid != spid:
                logging.info('service [%s] pid change detected: %s -> %s', sname, ser.pid, spid)
                ser.chgpid(spid)

        # set service to inactive if no status update for 5 minutes
        for sname, service in services.items():
            active = service.chkstatus(300)  # 300 seconds
            if not active:
                logging.info('service [%s] turn to inactive.', sname)

        self._parse_smetrics(smetrics, ser)
        return True

    def _parse_smetrics(self, metrics, service):
        for metric in metrics:
            logging.info('parsing %s of %s', metric.category, service.name)
            if 'pidstat' == metric.category:
                pidrep = parse_pidstat(metric.aid, metric.collect_at, service.id, metric.content)
                pidrep.save() if pidrep else None
            if 'jstat-gc' == metric.category:
                gcrep = parse_jstatgc(metric.aid, metric.collect_at, service.id, metric.content)
                gcrep.save() if gcrep else None

    def _agent_stop(self, msg):
        return True

    def find_agent(self, aid):
        return self._agents.get(aid, None)

    def start(self):
        logging.info('master started and listening on %s', self._addr)
        self._server = SocketServer.ThreadingTCPServer(self._addr, AgentRequestHandler)
        self._server.serve_forever()

    def handle_msg(self, msg, client_addr):
        logging.info('handle msg %s, client=%s.', msg, client_addr)
        return self._handlers[msg.msg_type](msg)

    def inactive_agent(self, agentid):
        agent = self._agents[agentid]
        return agent

    def stop(self):
        self._server.server_close()


def master_main():
    create_schema()
    global _MASTER
    _MASTER = Master('0.0.0.0')
    _MASTER.start()


if __name__ == '__main__':
    master_main()