#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Created on 2017-12-22
@author: foxty
"""

import unittest
import os
import time
import model
import content_parser
from datetime import datetime, timedelta
from uuid import uuid4
from common import Msg
from master import Master, DataKeeper


class BaseDBTest(unittest.TestCase):
    def setUp(self):
        dbconfig = {
            'info': {
                'type': 'sqlite',
                'url': 'test.sqlite3',
                'user': 'root'
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
        model.NCPUReport.delete()
        model.NMemoryReport.delete()
        model.NDiskReport.delete()
        model.NSystemReport.delete()
        model.SMetric.delete()
        model.SInfo.delete()
        model.SInfoHistory.delete()
        model.SJstatGCReport.delete()
        model.SPidstatReport.delete()


class ReportModelTest(unittest.TestCase):
    def test_mem_report(self):
        memrep = model.NMemoryReport(total_mem=1000, used_mem=100, free_mem=900)
        self.assertEqual(100*100/1000, memrep.used_util)
        self.assertEqual(900*100/1000, memrep.free_util)

        memrep = model.NMemoryReport(total_mem=1100, used_mem=100, free_mem=900)
        self.assertEqual(100*100/1100, memrep.used_util)
        self.assertEqual(900*100/1100, memrep.free_util)

        memrep = model.NMemoryReport(total_mem=None, used_mem=100, free_mem=900)
        self.assertEqual(None, memrep.used_util)
        self.assertEqual(None, memrep.free_util)

    def test_cpu_report(self):
        cpurep = model.NCPUReport(us=None, sy=100)
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
        _FIELDS = ['id', 'a1', 'a2', 'a3']

    def test_model(self):
        m = ModelTest.ModelA()
        self.assertIsNone(m.a1)

    def test_model_invalidfield(self):
        with self.assertRaises(model.InvalidFieldError) as cm:
            ModelTest.ModelA(a4=1)
            self.assertEqual('a4', cm.exception.msg)
        with self.assertRaises(model.InvalidFieldError) as cm:
            ModelTest.ModelA().non_exist_field1
            self.assertEqual('field a non_exist_field1 not defined.', cm.exception.msg)
        with self.assertRaises(model.InvalidFieldError) as cm:
            ModelTest.ModelA().non_exist_field2 = 1
            self.assertEqual('field a non_exist_field2 not defined.', cm.exception.msg)

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


class TSDModelTest(unittest.TestCase):
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
        sinfo = model.SInfo(id=id, aid='1', name='serv', pid='123', last_report_at=datetime.now())
        sinfo.save()
        self.assertEqual('1', sinfo.aid)
        self.assertEqual('serv', sinfo.name)
        sinfo.chgpid('456', ct)

        sinfo1 = sinfo.query_by_aid('1')[0]
        self.assertEqual(sinfo, sinfo1)
        self.assertEqual('456', sinfo1.pid)

        history = model.SInfoHistory.query()
        self.assertEqual(1, len(history))
        self.assertEqual(ct, history[0].collect_at)


class SPidstatReportTest(BaseDBTest):

    def test_base(self):
        ctime = datetime.now()
        id = uuid4().hex
        r = model.SPidstatReport(aid='1', service_id=id, collect_at=ctime)
        r.save()
        self.assertEqual('1', r.aid)
        self.assertEqual(id, r.service_id)
        self.assertEqual(ctime, r.collect_at)

    def test_chrono(self):
        sid = uuid4().hex
        now = datetime.now()
        prev_hour = now - timedelta(hours=1)
        next_hour = now + timedelta(hours=1)
        r1 = model.SPidstatReport(aid='1', service_id=sid, collect_at=prev_hour, tid=1, cpu_us=10, recv_at=next_hour)
        r1.save()
        r2 = model.SPidstatReport(aid='1', service_id=sid, collect_at=now, tid=1, cpu_us=20, recv_at=now)
        r2.save()
        r3 = model.SPidstatReport(aid='1', service_id=sid, collect_at=next_hour, tid=1, cpu_us=30, recv_at=prev_hour)
        r3.save()

        l1 = model.SPidstatReport.query_by_ctime(sid, now - timedelta(hours=1.5), now)
        self.assertEqual(2, len(l1))
        self.assertEqual(prev_hour, l1[0].collect_at)
        self.assertEqual(now, l1[1].collect_at)

        l1 = model.SPidstatReport.query_by_rtime(sid, now - timedelta(hours=1.5), now)
        self.assertEqual(2, len(l1))
        self.assertEqual(now, l1[0].collect_at)
        self.assertEqual(next_hour, l1[1].collect_at)


class SJstatReportTest(unittest.TestCase):

    def test_calc(self):
        rep = model.SJstatGCReport(ts=100, ygc=3, ygct=15.0, fgc=2, fgct=5.0, gct=20.0)
        self.assertEqual(5, rep.avg_ygct())
        self.assertEqual(2.5, rep.avg_fgct())
        self.assertEqual(0.8, rep.throughput())

    def test_to_gcstat(self):
        ctime = datetime.now()
        rep = model.SJstatGCReport(ts=100, service_id='sid', collect_at=ctime,
                                   ygc=3, ygct=15.0, fgc=2, fgct=5.0, gct=20.0)
        gcstat = rep.to_gcstat('test')
        self.assertEqual(model.JavaGCStat(category='test', start_at=ctime - timedelta(seconds=100), end_at=ctime,
                                          samples=0, ygc=3, ygct=15.0, avg_ygct=5.0, fgc=2, fgct=5.0, avg_fgct=2.5,
                                          throughput=0.8), gcstat)

    def test_sub(self):
        rep1 = model.SJstatGCReport(ts=100, ygc=3, ygct=15.0, fgc=2, fgct=5.0, gct=20.0)
        rep2 = model.SJstatGCReport(ts=20, ygc=1, ygct=10.0, fgc=1, fgct=3.0, gct=15.0)
        sub = rep1 - rep2
        self.assertEqual(model.SJstatGCReport(ts=80, ygc=2, ygct=5.0, fgc=1, fgct=2.0, gct=5.0), sub)

    def test_add(self):
        rep1 = model.SJstatGCReport(ts=100, ygc=3, ygct=15.0, fgc=2, fgct=5.0, gct=20.0)
        rep2 = model.SJstatGCReport(ts=20, ygc=1, ygct=10.0, fgc=1, fgct=3.0, gct=15.0)
        add = rep1 + rep2
        self.assertEqual(model.SJstatGCReport(ts=120, ygc=4, ygct=25.0, fgc=3, fgct=8.0, gct=35.0), add)


class MasterDAOTest(BaseDBTest):

    def test_add_nmemory(self):
        mem = model.NMemoryReport(aid='12345678', collect_at=datetime.now(),
                               total_mem=100, used_mem=50, cache_mem=10, free_mem=50,
                               total_swap=100, used_swap=20, free_swap=80)
        mem.save()

        mems = model.NMemoryReport.query_by_ctime('12345678',
                                               datetime.now() - timedelta(days=1),
                                               datetime.now() + timedelta(days=1))
        self.assertEqual(1, len(mems))
        self.assertEqual(mem, mems[0])

    def test_add_sysreport(self):
        sys = model.NSystemReport(aid='123', collect_at=datetime.now(),
                               uptime=12345, users=5, load1=1, load5=5, load15=15,
                               procs_r=1, procs_b=2, sys_in=1, sys_cs=2)
        sys.save()
        reports = model.NSystemReport.query_by_ctime('123', datetime.now() - timedelta(hours=1),
                                                  datetime.now() + timedelta(hours=1))
        self.assertEqual(1, len(reports))
        self.assertEqual(sys, reports[0])

    def test_add_cpureport(self):
        cpu = model.NCPUReport(aid='123', collect_at=datetime.now(),
                            us=2, sy=18, id=80, wa=0, st=0)
        cpu.save()
        cpus = model.NCPUReport.query_by_ctime('123', datetime.now() - timedelta(hours=1),
                                            datetime.now() + timedelta(hours=1))
        self.assertEqual(1, len(cpus))
        self.assertEqual(cpu, cpus[0])

    def test_cpu_chrono(self):
        now = datetime.now()
        prev_hour = now - timedelta(hours=1)
        cpu1 = model.NCPUReport(aid='123', collect_at=prev_hour, us=1, recv_at=now)
        cpu1.save()
        cpu2 = model.NCPUReport(aid='123', collect_at=now, us=2, recv_at=prev_hour)
        cpu2. save()

        cpus = model.NCPUReport.query()
        self.assertEqual(2, len(cpus))

        cpus = model.NCPUReport.query_by_ctime('123', start=prev_hour-timedelta(minutes=30), end=prev_hour+timedelta(minutes=30))
        self.assertEqual(1, len(cpus))
        self.assertEqual(cpu1, cpus[0])

        cpus = model.NCPUReport.query_by_rtime('123', start=now-timedelta(minutes=30), end=now+timedelta(minutes=30))
        self.assertEqual(1, len(cpus))
        self.assertEqual(cpu1, cpus[0])

    def test_add_diskreports(self):
        dr1 = model.NDiskReport(aid='123', collect_at=datetime.now(),
                             fs="/", size=1024, used=256, available=768, used_util='25%', mount_point="/root")
        dr2 = model.NDiskReport(aid='123', collect_at=datetime.now(),
                             fs="/abc", size=1024, used=256, available=768, used_util='25%', mount_point="/var")
        drs = [dr1, dr2]
        model.NDiskReport.save_all(drs)
        reports = model.NDiskReport.query_by_ctime('123', datetime.now() - timedelta(hours=1),
                                                datetime.now() + timedelta(hours=1))
        self.assertEqual(2, len(reports))
        self.assertEqual(dr1, reports[0])
        self.assertEqual(dr2, reports[1])


if __name__ == '__main__':
    unittest.main()