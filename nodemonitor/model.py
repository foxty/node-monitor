#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Created on 2017-12-22
@author: foxty

dao and model for master

"""

import os
import logging
import sqlite3
from collections import namedtuple
from datetime import datetime, timedelta


DB_PATH = '/opt/node-monitor/db/'
DB_NAME = DB_PATH + 'master.db'
if not os.path.exists(DB_PATH):
    logging.warn('create folder for database file %s', DB_PATH)
    os.makedirs(DB_PATH)

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
    
    CREATE TABLE IF NOT EXISTS service_history(aid, service_id, pid, collect_at timestamp, recv_at timestamp);
    
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


def dao(f):
    def dao_decorator(*kargs, **kdargs):
        with sqlite3.connect(DB_NAME,
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


class InvalidFieldError(Exception): pass


class NoPKError(Exception): pass


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

    def add_history(self, collect_at):
        SInfoHistory(aid=self.aid, service_id=self.id, pid=self.pid, collect_at=collect_at, recv_at=datetime.now()).save()

    def chgpid(self, newpid, collect_at):
        self.set(pid=newpid)
        self.add_history(collect_at)

    def chkstatus(self, threshold_secs):
        active = False
        if self.last_report_at:
            now = datetime.now()
            dt = now - self.last_report_at
            active = dt.seconds <= threshold_secs or self.last_report_at >= now
        self.set(status=self.STATUS_ACT if active else self.STATUS_INACT)
        return active

    @classmethod
    def byid(cls, id):
        return cls.query(where='id=?', params=[id])

    @classmethod
    def query_by_aid(cls, aid):
        return cls.query(where='aid=?', orderby='name', params=[aid])


class SInfoHistory(Model, ServiceChronoModel):
    _TABLE = 'service_history'
    _FIELDS = ['aid','service_id', 'pid', 'collect_at', 'recv_at']


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

    def __sub__(self, other):
        return SJstatGCReport(aid=self.aid, service_id=self.service_id, collect_at=self.collect_at,
                              ts=self.ts - other.ts, ygc=self.ygc - other.ygc, ygct=self.ygct - other.ygct,
                              fgc=self.fgc - other.fgc, fgct=self.fgct - other.fgct, gct=self.gct - other.gct)

    def __add__(self, other):
        collect_at = other.collect_at if other.collect_at > self.collect_at else self.collect_at
        return SJstatGCReport(aid=self.aid, service_id=self.service_id, collect_at=collect_at,
                              ts=self.ts + other.ts, ygc=self.ygc + other.ygc, ygct=self.ygct + other.ygct,
                              fgc=self.fgc + other.fgc, fgct=self.fgct + other.fgct, gct=self.gct + other.gct)

    def avg_ygct(self):
        return self.ygct/self.ygc if self.ygc > 0 else 0

    def avg_fgct(self):
        return self.fgct/self.fgc if self.fgc > 0 else 0

    def throughput(self):
        return 1 - self.gct/self.ts

    def to_gcstat(self, category):
        start_at = self.collect_at - timedelta(seconds=self.ts)
        return JavaGCStat(category=category, start_at=start_at, end_at=self.collect_at, samples=0,
                          ygc=self.ygc, ygct=self.ygct, avg_ygct=self.avg_ygct(),
                          fgc=self.fgc, fgct=self.fgct, avg_fgct=self.avg_fgct(),
                          throughput=self.throughput())

    @classmethod
    def lst_report_by_aid(cls, aid, count):
        return cls.query(where='aid=?', orderby='collect_at DESC', params=[aid], limit=count)


class JavaGCStat(Model):
    _FIELDS = ['category', 'start_at', 'end_at', 'samples',
               'ygc', 'ygct', 'avg_ygct', 'fgc', 'fgct', 'avg_fgct', 'throughput']


class Alarm(Model):
    _TABLE = ""
    _FIELDS = [""]