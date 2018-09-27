#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Created on 2017-12-22
@author: foxty

dao and model for master

"""

import logging
import os
import psycopg2
import requests
from enum import Enum
from datetime import datetime, timedelta

DB_CONFIG = None
_EPOC = datetime(1970, 1, 1)


def init_db(dbconfig, schema = None):
    """
    setup database by sqlite3
    :return:
    """
    global DB_CONFIG
    DB_CONFIG = dbconfig
    logging.info('init db with config: %s', dbconfig)
    if schema is not None:
        logging.info('creating schema for %s', DB_CONFIG['info'])
        _create_schema(schema)


def dao(db):
    def db_info(f):
        def dao_decorator(*kargs, **kdargs):
            infodb = DB_CONFIG['info']
            dbhost = infodb['host']
            dbname = infodb['name']
            user = infodb['user']
            password = infodb['password']
            # redo the operation until it success
            retry = 0
            while True:
                try:
                    with psycopg2.connect(host=dbhost, database=dbname, user=user, password=password) as conn:
                        c = conn.cursor()
                        kdargs['cursor'] = c
                        result = f(*kargs, **kdargs)
                        conn.commit()
                        c.close()
                        return result
                except psycopg2.OperationalError as oe:
                    retry += 1
                    logging.error('error while connecting to postgres db, retry %d...', retry)
        return dao_decorator

    def db_tsd(f):
        def dao_decorator(*kargs, **kdargs):
            dburl = 'http://%s:%s' % (DB_CONFIG['tsd']['host'], DB_CONFIG['tsd']['port'])
            kdargs['dburl'] = dburl
            r = f(*kargs, **kdargs)
            return r
        return dao_decorator
    if callable(db):
        return db_info(db)
    else:
        return db_info if db == 'info' else db_tsd


@dao
def _create_schema(schema, cursor):
    with open(schema, 'r') as f:
        cursor.execute(f.read())


@dao
def _drop_schema(cursor):
    logging.info('drop schema.')
    cursor.execute("""
    DROP TABLE agent;
    DROP TABLE node_metric_raw;
    DROP TABLE service_metric_raw;
    DROP TABLE service;
    DROP TABLE service_history;
    """)


class InvalidFieldError(Exception):
    pass


class NoPKError(Exception):
    pass


class InvalidAggError(Exception):
    pass


class Model(dict):
    _MAPPINGS = {}
    _TABLE = 'model'
    _FIELDS = []
    _PK = ["_id"]
    _ISQL = None

    def __new__(cls, *args, **kwargs):
        if not cls._MAPPINGS.has_key(cls._TABLE):
            cls._MAPPINGS[cls._TABLE] = cls
        return super(Model, cls).__new__(cls, args, kwargs)

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
            raise InvalidFieldError('field "%s.%s" not defined.' % (self._TABLE, item))

    def __setattr__(self, key, value):
        if key in self._FIELDS:
            self[key] = value
        else:
            raise InvalidFieldError('field "%s.%s" not defined.' % (self._TABLE, key))

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
    def remove(self, cursor):
        if not self._PK:
            raise NoPKError(self._TABLE)
        logging.debug('delete model %s with %s', self._TABLE,)
        wherephrase = ' AND '.join(['%s=?' % pk for pk in self._PK])
        pkvalues = tuple([self.get(pk) for pk in self._PK])
        sql = 'DELETE FROM %s WHERE %s' % (self._TABLE, wherephrase)
        sql = sql.replace('?', '%s')
        params = pkvalues
        logging.debug('%s : %s', sql, params)
        cursor.execute(sql, params)

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
            sql = sql.replace('?', '%s')
            params = values + pkvalues
            logging.debug('%s : %s', sql, params)
            cursor.execute(sql, params)
            self.update(kwargs)

    @classmethod
    def isql(cls):
        if not cls._ISQL:
            cls._ISQL = 'INSERT INTO %s (%s) VALUES(%s)' % (cls._TABLE, ','.join(cls._FIELDS), ','.join('?' * len(cls._FIELDS)))
            cls._ISQL = cls._ISQL.replace('?', '%s')
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
                                                 'WHERE %s' % where.replace('?', '%s') if where else '',
                                                 'ORDER BY %s' % orderby if orderby else '',
                                                 'LIMIT %d' % limit if limit is not None else '',
                                                 'OFFSET %d' % offset if offset is not None else '')
        logging.debug('%s : %s', sql, params)
        cursor.execute(sql, params if params else [])
        result = cursor.fetchall()
        return [cls(*r) for r in result]

    @classmethod
    @dao
    def delete(cls, where=None, params=None, cursor=None):
        """
        Delete records for this model
        :param where:
        :param params:
        :param cursor:
        :return: deleted count
        """
        sql = 'DELETE FROM %s %s' % (cls._TABLE, 'WHERE %s' % where if where else '')
        sql = sql.replace('?', '%s')
        logging.debug('%s : %s', sql, params)
        cursor.execute(sql, params if params else [])

    @classmethod
    @dao
    def count(cls, where=None, params=None, cursor=None):
        cursor.execute('SELECT COUNT(1) FROM %s %s' % (cls._TABLE, 'WHERE ' + where.replace('?', '%s') if where else ''),
                       params if params else ())
        r = cursor.fetchone()
        return r[0] if r else 0

    @classmethod
    def find_model(cls, tablename):
        return cls._MAPPINGS[tablename]


class TSDAgg(Enum):
    AVG = 'avg'
    COUNT = 'count'
    DEV = 'dev'
    EP50R3 = 'ep50r3'
    EP50R7 = 'ep50r7'
    EP75R3 = 'ep75r3'
    EP75R7 = 'ep75r7'
    EP90R3 = 'ep90r3'
    EP90R7 = 'ep90r7'
    EP95R3 = 'ep95r3'
    EP95R7 = 'ep95r7'
    EP99R3 = 'ep99r3'
    EP99R7 = 'ep99r7'
    EP999R3 = 'ep999r'
    EP999R7 = 'ep999r'
    FIRST = 'first'
    LAST = 'last'
    MIMMIN = 'mimmin'
    MIMMAX = 'mimmax'
    MIN = 'min'
    MAX = 'max'
    NONE = 'none'
    P50 = 'p50'
    P75 = 'p75'
    P90 = 'p90'
    P95 = 'p95'
    P99 = 'p99'
    P999 = 'p999'
    SUM = 'sum'
    ZIMSUM = 'zimsum'


class TSDModel(dict):
    _METRIC_PREFIX = 'model'
    _METRICS = []
    _TAGS = []

    def __init__(self, **kwargs):
        self.timestamp = kwargs.pop('timestamp')
        upd = None
        kwupd = self._check_updates(kwargs)
        upd = kwupd if not upd else upd + kwupd
        if upd:
            self.update({k: v for k, v in upd if v is not None})

    def __getattr__(self, item):
        if item in self._METRICS or item in self._TAGS or item == 'timestamp':
            return self.get(item, None)
        else:
            raise InvalidFieldError('model field "%s" not defined.' % item)

    def __setattr__(self, key, value):
        if key in self._METRICS or key in self._TAGS or key == 'timestamp':
            self[key] = value
        else:
            raise InvalidFieldError('field %s not defined.' % key)

    def _check_updates(self, kwargs):
        if kwargs:
            diff = kwargs.viewkeys() - set(self._METRICS + self._TAGS)
            if diff:
                raise InvalidFieldError(','.join(diff))
            else:
                upd = kwargs.items()
        else:
            upd = []
        return upd

    def build_save_content(self):
        values = []
        for metric in self._METRICS:
            fullmetric = self._METRIC_PREFIX + '.' + metric
            if self.get(metric, None) is None:
                logging.info('metric %s is none for tags %s ', fullmetric, self._TAGS)
                continue
            value = dict()
            value['metric'] = fullmetric
            value['timestamp'] = (self.timestamp - _EPOC).total_seconds()
            value['value'] = self[metric]
            value['tags'] = {t: self[t] for t in self._TAGS}
            values.append(value)
        return values

    @dao('tsd')
    def save(self, dburl):
        """
        save current model to opentsdb
        """
        logging.debug('saving model %s to %s', self, dburl)
        values = self.build_save_content()
        logging.debug('metrics %s will post to remote tsdb %s', values, dburl)
        try:
            resp = requests.post(dburl + '/api/put?details', json=values)
            rj = resp.json()
            logging.info('metrics of %s saved to tsdb with %s success, %s failed, errors=%s',
                        self._METRIC_PREFIX, rj['success'], rj['failed'], rj['errors'])
            re = resp.status_code == 204
        except Exception:
            logging.exception('save metrics for %s failed.', self._METRIC_PREFIX)
            re = False
        return re

    @classmethod
    def save_all(cls, records):
        return [re.save() for re in records]

    @classmethod
    def build_query_body(cls, start, end, agg, metrics, tags, downsample, rateops):
        content = {'start': start, 'queries': []}
        if end is not None:
            content['end'] = end
        if type(agg) is not TSDAgg:
            raise InvalidAggError(agg)
        qs = content['queries']
        if metrics is None:
            metrics = cls._METRICS
        elif not isinstance(metrics, list):
            metrics = [metrics]
        for m in metrics:
            q = {
                'aggregator': agg.value,
                'metric': cls._METRIC_PREFIX + '.' + m
            }
            if tags is not None:
                q['tags'] = tags
            if downsample is not None:
                q['downsample'] = downsample
            if rateops is not None:
                q['rate'] = True
                q['rateoption'] = rateops
            qs.append(q)
            logging.debug('new q %s added', q)
        return content

    @classmethod
    @dao('tsd')
    def query(cls, start, end=None, agg=TSDAgg.NONE, metrics=None, tags=None,
              downsample=None, rateops=None, dburl=None):
        body = cls.build_query_body(start, end, agg, metrics, tags, downsample, rateops)
        metrics_data = {}
        try:
            resp = requests.post(dburl + '/api/query', json=body)
            resp_json = resp.json()
            if resp.status_code == 200:
                for m in resp_json:
                    mname = m['metric']
                    if mname not in metrics_data:
                        metrics_data[mname] = []
                    metrics_data[mname].append(m)
                metrics_data['downsample'] = downsample is not None
            else:
                logging.error('query of %s from %s failed, resp=%s', body, dburl, resp_json)
        except Exception:
            logging.exception('query of %s from %s failed.', body, dburl)
        return metrics_data


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
               'last_cpu_util', 'last_mem_util', 'last_sys_load1', 'last_sys_cs', 'status']
    _PK = ['aid']

    def __str__(self):
        return '[Agent:aid=%s, name=%s, host=%s, status=%s]' % (self.aid, self.name, self.host, self.status)

    @classmethod
    def get_by_id(cls, aid):
        r = cls.query(where='aid=?', params=[aid])
        return r[0] if r else None

    @classmethod
    def query_by_load1(cls, count=10):
        return cls.query(orderby='last_sys_load1 DESC', limit=count)


class NMetric(Model, AgentChronoModel):
    _TABLE = 'node_metric_raw'
    _FIELDS = ['aid', 'collect_at', 'category', 'content', 'recv_at']


class NMemoryReport(TSDModel):
    _METRIC_PREFIX = 'node.memory'
    _METRICS = ['total_mem', 'used_mem', 'free_mem', 'cache_mem', 'total_swap', 'used_swap', 'free_swap']
    _TAGS = ['aid']

    @property
    def used_util(self):
        return self.used_mem*100/self.total_mem if self.used_mem and self.total_mem else None

    @property
    def free_util(self):
        return self.free_mem*100/self.total_mem if self.free_mem and self.total_mem else None


class NCPUReport(TSDModel):
    _METRIC_PREFIX = 'node.cpu'
    _METRICS = ['us', 'sy', 'id', 'wa', 'st']
    _TAGS = ['aid']

    @property
    def used_util(self):
        return self.us + self.sy if self.us is not None and self.sy is not None else None


class NSystemReport(TSDModel):
    _METRIC_PREFIX = 'node.system'
    _METRICS = ['uptime', 'users', 'load1', 'load5',
                'load15', 'procs_r', 'procs_b', 'sys_in', 'sys_cs']
    _TAGS = ['aid']


class NDiskReport(TSDModel):
    _METRIC_PREFIX = 'node.disk'
    _METRICS = ['size', 'used', 'available', 'used_util']
    _TAGS = ['aid', 'fs', 'mount_point']


class SMetric(Model, AgentChronoModel):
    _TABLE = 'service_metric_raw'
    _FIELDS = ['aid', 'collect_at', 'name', 'pid', 'category', 'content', 'recv_at']


class SInfo(Model):
    _TABLE = 'service'
    _FIELDS = ['id', 'aid', 'name', 'pid', 'type', 'last_report_at', 'status']
    _PK = ['id']

    STATUS_ACT = 'active'
    STATUS_INACT = 'inactive'

    def __str__(self):
        return '[SInfo: aid=%s, name=%s, pid=%s]' % (self.aid, self.name, self.pid)

    def add_history(self, collect_at):
        SInfoHistory(aid=self.aid, service_id=self.id, pid=self.pid, collect_at=collect_at, recv_at=datetime.utcnow()).save()

    def chgpid(self, newpid, collect_at):
        self.set(pid=newpid)
        self.add_history(collect_at)

    def chkstatus(self, threshold_secs):
        active = False
        if self.last_report_at:
            now = datetime.utcnow()
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


class SPidstatReport(TSDModel):
    _METRIC_PREFIX = 'service.pidstat'
    _METRICS = ['cpu_us', 'cpu_sy', 'cpu_gu', 'cpu_util', 'mem_minflt', 'mem_majflt',
                'mem_vsz', 'mem_rss', 'mem_util', 'disk_rd', 'disk_wr', 'disk_ccwr']
    _TAGS = ['aid', 'service_id', 'tid']


class SJstatGCReport(TSDModel):
    _METRIC_PREFIX = 'service.jstatgc'
    _METRICS = ['ts', 's0c', 's1c', 's0u', 's1u', 'ec', 'eu', 'oc', 'ou', 'mc', 'mu',
                'ccsc', 'ccsu', 'ygc', 'ygct', 'fgc', 'fgct', 'gct']
    _TAGS = ['aid', 'service_id']

    def __sub__(self, other):
        return SJstatGCReport(aid=self.aid, service_id=self.service_id, timestamp=self.timestamp,
                              ts=self.ts - other.ts, ygc=self.ygc - other.ygc, ygct=self.ygct - other.ygct,
                              fgc=self.fgc - other.fgc, fgct=self.fgct - other.fgct, gct=self.gct - other.gct)

    def __add__(self, other):
        timestamp = other.timestamp if other.timestamp > self.timestamp else self.timestamp
        return SJstatGCReport(aid=self.aid, service_id=self.service_id, timestamp=timestamp,
                              ts=self.ts + other.ts, ygc=self.ygc + other.ygc, ygct=self.ygct + other.ygct,
                              fgc=self.fgc + other.fgc, fgct=self.fgct + other.fgct, gct=self.gct + other.gct)

    def avg_ygct(self):
        return self.ygct/self.ygc if self.ygc > 0 else 0

    def avg_fgct(self):
        return self.fgct/self.fgc if self.fgc > 0 else 0

    def throughput(self):
        return 1 - self.gct/self.ts

    def to_gcstat(self, category):
        start_at = self.timestamp - timedelta(seconds=self.ts)
        return JavaGCStat(category=category, start_at=start_at, end_at=self.timestamp, samples=0,
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