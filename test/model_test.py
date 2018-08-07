#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Created on 2017-12-22
@author: foxty
"""

import unittest
import os
import model
import mock
import requests
from datetime import datetime, timedelta
from uuid import uuid4


class BaseDBTest(unittest.TestCase):
    def setUp(self):
        dbconfig = {
            'info': {
                'type': 'sqlite',
                'host': '192.168.99.100',
                'name': 'node-monitor',
                'user': 'node-monitor',
                'password': 'node-monitor'
            },
            'tsd': {
                'type': 'opentsdb',
                'host': 'localhost',
                'port': 4242
            }
        }
        model.init_db(dbconfig, '../conf/schema.sql')

    def tearDown(self):
        model.Agent.delete()
        model.NMetric.delete()
        model.SMetric.delete()
        model.SInfo.delete()
        model.SInfoHistory.delete()


class ReportModelTest(unittest.TestCase):
    def test_mem_report(self):
        ct = datetime.now()
        memrep = model.NMemoryReport(timestamp=ct, total_mem=1000, used_mem=100, free_mem=900)
        self.assertEqual(100*100/1000, memrep.used_util)
        self.assertEqual(900*100/1000, memrep.free_util)

        memrep = model.NMemoryReport(timestamp=ct, total_mem=1100, used_mem=100, free_mem=900)
        self.assertEqual(100*100/1100, memrep.used_util)
        self.assertEqual(900*100/1100, memrep.free_util)

        memrep = model.NMemoryReport(timestamp=ct, total_mem=None, used_mem=100, free_mem=900)
        self.assertEqual(None, memrep.used_util)
        self.assertEqual(None, memrep.free_util)

    def test_cpu_report(self):
        cpurep = model.NCPUReport(timestamp=datetime.now(), us=None, sy=100)
        self.assertEqual(None, cpurep.used_util)

        cpurep.us=1
        cpurep.sy=None
        self.assertEqual(None, cpurep.used_util)

        cpurep.us=1
        cpurep.sy=2
        self.assertEqual(3, cpurep.used_util)

        cpurep.us=0
        cpurep.sy=0
        self.assertEqual(0, cpurep.used_util)


class ModelTest(unittest.TestCase):

    class ModelA(model.Model):
        _TABLE = 'tablea'
        _FIELDS = ['id', 'a1', 'a2', 'a3']

    def test_model(self):
        m = ModelTest.ModelA()
        self.assertIsNone(m.a1)

    def test_model_invalidfield(self):
        with self.assertRaises(model.InvalidFieldError) as cm:
            ModelTest.ModelA(a4=1)
        self.assertEqual('a4', cm.exception.message)
        with self.assertRaises(model.InvalidFieldError) as cm:
            ModelTest.ModelA().non_exist_field1
        self.assertEqual('field "tablea.non_exist_field1" not defined.', cm.exception.message)
        with self.assertRaises(model.InvalidFieldError) as cm:
            ModelTest.ModelA().non_exist_field2 = 1
        self.assertEqual('field "tablea.non_exist_field2" not defined.', cm.exception.message)

    def test_astuple(self):
        ma = ModelTest.ModelA()
        t = ma.as_tuple()
        self.assertEqual((None, None, None, None), t)

        ma = ModelTest.ModelA(1, 2, 3, 4)
        t = ma.as_tuple()
        self.assertEqual((1, 2, 3, 4), t)

    def test_nonexsit_fields(self):
        ma = ModelTest.ModelA()
        self.assertEqual(0, len(ma))
        self.assertIsNone(ma.a1)

    def test_init_fromtuple(self):
        t = (1, 1, 2, 3)
        ma = ModelTest.ModelA(*t)
        self.assertEqual(4, len(ma))
        self.assertEqual(1, ma.a1)
        self.assertEqual(2, ma.a2)
        self.assertEqual(3, ma.a3)

    def test_init_with_seq_params(self):
        ma = ModelTest.ModelA(1, 2, 'a2', 3.3)
        self.assertEqual(4, len(ma))
        self.assertEqual(2, ma.a1)
        self.assertEqual('a2', ma.a2)
        self.assertEqual(3.3, ma.a3)

        ma = ModelTest.ModelA(1, 2, 'a2')
        self.assertEqual(3, len(ma))
        self.assertEqual(2, ma.a1)
        self.assertEqual('a2', ma.a2)
        self.assertEqual(None, ma.a3)

    def test_init_with_kv_params(self):
        ma = ModelTest.ModelA(a1=1, a2='a2', a3=3.3)
        self.assertEqual(3, len(ma))
        self.assertEqual(1, ma.a1)
        self.assertEqual('a2', ma.a2)
        self.assertEqual(3.3, ma.a3)

        ma = ModelTest.ModelA(a1=1, a3=3.3)
        self.assertEqual(2, len(ma))
        self.assertEqual(1, ma.a1)
        self.assertEqual(None, ma.a2)
        self.assertEqual(3.3, ma.a3)

    def test_init_with_mix_params(self):
        ma = ModelTest.ModelA(1, 2, 3, a2='a2', a3=3.3)
        self.assertEqual(4, len(ma))
        self.assertEqual(2, ma.a1)
        self.assertEqual('a2', ma.a2)
        self.assertEqual(3.3, ma.a3)


class TSDModelTest(BaseDBTest):
    class TSDModelA(model.TSDModel):
        _METRIC_PREFIX = 'test.prefix'
        _METRICS = ['m1', 'm2', 'm3']
        _TAGS = ['tag1', 'tag2']

    def test_creation(self):
        tm = TSDModelTest.TSDModelA(timestamp=123455)
        self.assertEqual(1, len(tm))
        self.assertEqual(123455, tm.timestamp)

        tm = TSDModelTest.TSDModelA(timestamp=1234, tag1=1, m1=11)
        self.assertEqual(3, len(tm))
        self.assertEqual(1234, tm.timestamp)
        self.assertEqual(1, tm.tag1)
        self.assertEqual(11, tm.m1)

    def test_save(self):
        with mock.patch('requests.Response') as resp:
            ts = datetime.now()
            resp.status_code = 400
            resp.json = mock.MagicMock(retrn_value={})
            requests.post = mock.Mock(return_value=resp)
            tm = TSDModelTest.TSDModelA(timestamp=ts, m1=1.1, m2=1.2, m3=1.3, tag1='t1', tag2='t2')
            re = tm.save()
            exp_ts = (ts - model._EPOC).total_seconds()
            tags = {'tag1': 't1', 'tag2': 't2'}
            expdata = [{
                'timestamp': exp_ts,
                'metric': 'test.prefix.m1',
                'value': 1.1,
                'tags': tags
            }, {
                'timestamp': exp_ts,
                'metric': 'test.prefix.m2',
                'value': 1.2,
                'tags': tags
            }, {
                'timestamp': exp_ts,
                'metric': 'test.prefix.m3',
                'value': 1.3,
                'tags': tags
            }]

            requests.post.assert_called_with('http://localhost:4242/api/put?details', json=expdata)
            requests.post.assert_called_once()
            self.assertFalse(re)

    def test_build_query_body(self):
        body = TSDModelTest.TSDModelA.build_query_body(start=123,
                                                       end=456,
                                                       agg=model.TSDAgg.AVG,
                                                       metrics=['m1', 'm2'],
                                                       tags={'tag1': '111', 'tag2': '222'},
                                                       downsample='5m-avg',
                                                       rateops=None)
        self.assertEqual({'end': 456,
                          'queries': [{'aggregator': 'avg',
                                       'downsample': '5m-avg',
                                       'metric': 'test.prefix.m1',
                                       'tags': {'tag1': '111', 'tag2': '222'}},
                                      {'aggregator': 'avg',
                                       'downsample': '5m-avg',
                                       'metric': 'test.prefix.m2',
                                       'tags': {'tag1': '111', 'tag2': '222'}}],
                          'start': 123}, body)


class AgentTest(BaseDBTest):

    def test_add_agent(self):
        aglist = model.Agent.query()
        self.assertEqual(0, len(aglist))

        ag = model.Agent('12345678', 'agent1', '127.0.0.1', datetime.now())
        ag.save()

        aglist = model.Agent.query()
        self.assertEqual(1, len(aglist))
        self.assertEqual(ag, aglist[0])

    def test_agent_query(self):
        ag1 = model.Agent('1', 'agent1', '127.0.0.1', datetime.now())
        ag1.save()
        ag2 = model.Agent('2', 'agent2', '127.0.0.2', datetime.now())
        ag2.save()
        ag3 = model.Agent('3', 'agent3', '127.0.0.3', datetime.now())
        ag3.save()

        agents = model.Agent.query()
        self.assertEqual(3, len(agents))

        agents = model.Agent.query(where='aid=?', params=['1'])
        self.assertEqual(1, len(agents))
        self.assertEqual(ag1, agents[0])

        agents = model.Agent.query(orderby='aid ASC')
        self.assertEqual(3, len(agents))
        self.assertEqual(ag1, agents[0])
        self.assertEqual(ag2, agents[1])
        self.assertEqual(ag3, agents[2])

        agents = model.Agent.query(orderby='aid ASC', offset=1, limit=2)
        self.assertEqual(2, len(agents))
        self.assertEqual(ag2, agents[0])
        self.assertEqual(ag3, agents[1])

    def test_agent_count(self):
        ag1 = model.Agent('1', 'agent1', '127.0.0.1', datetime.now())
        ag2 = model.Agent('2', 'agent2', '127.0.0.1', datetime.now())
        ag3 = model.Agent('3', 'agent3', '127.0.0.1', datetime.now())
        model.Agent.save_all([ag1, ag2, ag3])

        self.assertEqual(3, model.Agent.count())
        self.assertEqual(1, model.Agent.count(where='aid=?', params=['1']))
        self.assertEqual(2, model.Agent.count(where='aid>?', params=['1']))
        self.assertEqual(0, model.Agent.count(where='name=?', params=['1']))

    def test_update_agent(self):
        ag = model.Agent('12345678', 'agent1', '127.0.0.1', datetime.now())
        ag.save()
        ag.set(last_cpu_util=99, last_mem_util=55.5, last_sys_load1=1.1, last_sys_cs=123)
        aglist = model.Agent.query()
        self.assertEqual(1, len(aglist))
        nag = aglist[0]
        self.assertEqual(99, nag.last_cpu_util)
        self.assertEqual(55.5, nag.last_mem_util)
        self.assertEqual(1.1, nag.last_sys_load1)
        self.assertEqual(123, nag.last_sys_cs)

    def test_remove_agent(self):
        ag = model.Agent('12345678', 'agent1', '127.0.0.1', datetime.now())
        ag.save()
        agents = model.Agent.query()
        self.assertEqual(1, len(agents))
        self.assertEqual(ag, agents[0])
        ag.remove()
        agents = model.Agent.query()
        self.assertEqual(0, len(agents))


class SInfoTest(BaseDBTest):

    def test_basic(self):
        id0 = uuid4().hex
        id1 = uuid4().hex
        sinfo = model.SInfo(id=id0, name='service a')
        sinfo.save()
        sinfo.id = id1
        sinfo.name = 'service b'
        sinfo.save()
        infos = model.SInfo.query(orderby='name ASC')
        self.assertEqual(2, len(infos))
        self.assertEqual(id0, infos[0].id)
        self.assertEqual(id1, infos[1].id)

    def test_chkstatus(self):
        d1 = datetime.utcnow() - timedelta(seconds=100)
        sinfo = model.SInfo(last_report_at=d1, status=model.SInfo.STATUS_INACT)
        self.assertTrue(sinfo.chkstatus(200))
        self.assertFalse(sinfo.chkstatus(99))
        self.assertEqual(model.SInfo.STATUS_INACT, sinfo.status)

    def test_chkstatus_invaliddate(self):
        d = datetime.now() + timedelta(seconds=100)
        sinfo = model.SInfo(last_report_at=d, status=model.SInfo.STATUS_INACT)
        self.assertTrue(sinfo.chkstatus(200))
        self.assertTrue(sinfo.chkstatus(99))
        self.assertEqual(model.SInfo.STATUS_ACT, sinfo.status)

    def test_chgpid(self):
        ct = datetime.now()
        id = uuid4().hex
        sinfo = model.SInfo(id=id, aid='1', name='serv', pid=123, last_report_at=datetime.now())
        sinfo.save()
        self.assertEqual('1', sinfo.aid)
        self.assertEqual('serv', sinfo.name)
        sinfo.chgpid(456, ct)

        sinfo1 = sinfo.query_by_aid('1')[0]
        self.assertEqual(sinfo, sinfo1)
        self.assertEqual(456, sinfo1.pid)

        history = model.SInfoHistory.query()
        self.assertEqual(1, len(history))
        self.assertEqual(ct, history[0].collect_at)


class SPidstatReportTest(BaseDBTest):

    def test_base(self):
        ctime = datetime.now()
        id = uuid4().hex
        r = model.SPidstatReport(timestamp=ctime, aid='1', service_id=id)
        r.save()
        self.assertEqual('1', r.aid)
        self.assertEqual(id, r.service_id)
        self.assertEqual(ctime, r.timestamp)


class SJstatReportTest(unittest.TestCase):

    def test_calc(self):
        rep = model.SJstatGCReport(timestamp=datetime.now(), ts=100, ygc=3, ygct=15.0, fgc=2, fgct=5.0, gct=20.0)
        self.assertEqual(5, rep.avg_ygct())
        self.assertEqual(2.5, rep.avg_fgct())
        self.assertEqual(0.8, rep.throughput())

    def test_to_gcstat(self):
        ctime = datetime.now()
        rep = model.SJstatGCReport(timestamp=datetime.now(), ts=100, service_id='sid',
                                   ygc=3, ygct=15.0, fgc=2, fgct=5.0, gct=20.0)
        gcstat = rep.to_gcstat('test')
        self.assertEqual(model.JavaGCStat(category='test', start_at=ctime - timedelta(seconds=100), end_at=ctime,
                                          samples=0, ygc=3, ygct=15.0, avg_ygct=5.0, fgc=2, fgct=5.0, avg_fgct=2.5,
                                          throughput=0.8), gcstat)

    def test_sub(self):
        now = timestamp=datetime.now()
        rep1 = model.SJstatGCReport(timestamp=now, ts=100, ygc=3, ygct=15.0, fgc=2, fgct=5.0, gct=20.0)
        rep2 = model.SJstatGCReport(timestamp=now, ts=20, ygc=1, ygct=10.0, fgc=1, fgct=3.0, gct=15.0)
        sub = rep1 - rep2
        self.assertEqual(model.SJstatGCReport(timestamp=now, ts=80, ygc=2, ygct=5.0, fgc=1, fgct=2.0, gct=5.0), sub)

    def test_add(self):
        now = timestamp=datetime.now(),
        rep1 = model.SJstatGCReport(timestamp=now, ts=100, ygc=3, ygct=15.0, fgc=2, fgct=5.0, gct=20.0)
        rep2 = model.SJstatGCReport(timestamp=now, ts=20, ygc=1, ygct=10.0, fgc=1, fgct=3.0, gct=15.0)
        add = rep1 + rep2
        self.assertEqual(model.SJstatGCReport(timestamp=now, ts=120, ygc=4, ygct=25.0, fgc=3, fgct=8.0, gct=35.0), add)


if __name__ == '__main__':
    unittest.main()