#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Created on 2017-12-22
@author: foxty
"""

import unittest
import os
import sys
import socket
import master as nm
from datetime import datetime, timedelta

nm._MASTER_DB_NAME = 'test.db'


class BaseDBTest(unittest.TestCase):
    def setUp(self):
        if os.path.exists(nm._MASTER_DB_NAME):
            os.remove(nm._MASTER_DB_NAME)
        self.dao = nm.MasterDAO()

    def tearDown(self):
        if os.path.exists(nm._MASTER_DB_NAME):
            os.remove(nm._MASTER_DB_NAME)


class ModelTest(unittest.TestCase):

    class ModelA(nm.Model):
        FIELDS = ['a1', 'a2' , 'a3']

    def test_model(self):
        m = ModelTest.ModelA()
        self.assertIsNone(m.a_nont_exist_field)

    def test_astuple(self):
        ma = ModelTest.ModelA()
        t = ma.as_tuple()
        self.assertEqual((None, None, None), t)

        ma = ModelTest.ModelA(1,2,3)
        t = ma.as_tuple()
        self.assertEqual((1,2,3), t)

    def test_nonexsit_fields(self):
        ma = ModelTest.ModelA()
        self.assertEqual(0, len(ma))
        self.assertIsNone(ma.a1)

    def test_init_fromtuple(self):
        t = (1,2,3)
        ma = ModelTest.ModelA(*t)
        self.assertEqual(3, len(ma))
        self.assertEqual(1, ma.a1)
        self.assertEqual(2, ma.a2)
        self.assertEqual(3, ma.a3)

    def test_init_with_seq_params(self):
        ma = ModelTest.ModelA(1, 'a2', 3.3)
        self.assertEqual(3, len(ma))
        self.assertEqual(1, ma.a1)
        self.assertEqual('a2', ma.a2)
        self.assertEqual(3.3, ma.a3)

        ma = ModelTest.ModelA(1, 'a2')
        self.assertEqual(2, len(ma))
        self.assertEqual(1, ma.a1)
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
        ma = ModelTest.ModelA(1, 2, a2='a2', a3=3.3)
        self.assertEqual(3, len(ma))
        self.assertEqual(1, ma.a1)
        self.assertEqual('a2', ma.a2)
        self.assertEqual(3.3, ma.a3)


class ReportModelTest(unittest.TestCase):
    def test_mem_report(self):
        memrep = nm.NMemoryReport(total_mem=1000, used_mem=100, free_mem=900)
        self.assertEqual(100*100/1000, memrep.used_util)
        self.assertEqual(900*100/1000, memrep.free_util)

        memrep = nm.NMemoryReport(total_mem=1100, used_mem=100, free_mem=900)
        self.assertEqual(100*100/1100, memrep.used_util)
        self.assertEqual(900*100/1100, memrep.free_util)

        memrep = nm.NMemoryReport(total_mem=None, used_mem=100, free_mem=900)
        self.assertEqual(None, memrep.used_util)
        self.assertEqual(None, memrep.free_util)

    def test_cpu_report(self):
        cpurep = nm.NCPUReport(us=None, sy=100)
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


class GlobalFuncTest(unittest.TestCase):

    def test_parse_w_solaris(self):
        m = nm.Master()
        ctime = datetime.now()
        r = nm.parse_w('2', collect_time=ctime, content='''
        9:11pm  up 43 day(s),  8:52,  11 user,  load average: 2.38, 2.41, 2.41
        User     tty           login@  idle   JCPU   PCPU  what
        root     pts/4        27Dec17           18         -bash
        ''')
        self.assertEqual('2', r.aid)
        self.assertEqual(ctime, r.collect_at)
        self.assertEqual(43*24*3600, r.uptime)
        self.assertEqual(11, r.users)
        self.assertEqual(2.38, r.load1)
        self.assertEqual(2.41, r.load5)
        self.assertEqual(2.41, r.load15)
        self.assertIsNone(r.procs_r)
        self.assertIsNone(r.procs_b)
        self.assertIsNone(r.sys_in)
        self.assertIsNone(r.sys_cs)

    def test_parse_vmstat_linux(self):
        m = nm.Master()
        ctime = datetime.now()
        r, procs_r, procs_b, sys_in, sys_cs = nm.parse_vmstat('1', collect_time=ctime, content='''
         procs -----------memory---------- ---swap-- -----io---- --system-- -----cpu-----
         r  b   swpd   free   buff  cache   si   so    bi    bo   in   cs us sy id wa st
         0  0      0 13540540 161232 2972924    0    0     2    17   84   25  0  0 99  1  0
         10  5      0 13540532 161232 2972956    0    0     0    48  310  550  0  0 99  1  0
        ''')
        self.assertEqual('1', r.aid)
        self.assertEqual(ctime, r.collect_at)
        self.assertEqual(0, r.us)
        self.assertEqual(0, r.sy)
        self.assertEqual(99, r.id)
        self.assertEqual(1, r.wa)
        self.assertEqual(0, r.st)
        self.assertEqual(10, procs_r)
        self.assertEqual(5, procs_b)
        self.assertEqual(310, sys_in)
        self.assertEqual(550, sys_cs)

    def test_parse_vmstat_solaris(self):
        m = nm.Master()
        ctime = datetime.now()
        r, procs_r, procs_b, sys_in, sys_cs = nm.parse_vmstat('1', collect_time=ctime, content='''
         kthr      memory            page            disk          faults      cpu
         r b w   swap  free  re  mf pi po fr de sr s0 s1 s2 --   in   sy   cs us sy id
         1 0 0 40259268 4601776 32 543 3 0 0  0  0 -0  0 20  0 3092 3291 2996  1  5 93
         1 2 0 37758804 2545032 14 53 0 0  0  0  0  0  0  1  0 2236 1625 2002  1  1 98
        ''')
        self.assertEqual('1', r.aid)
        self.assertEqual(ctime, r.collect_at)
        self.assertEqual(1, r.us)
        self.assertEqual(1, r.sy)
        self.assertEqual(98, r.id)
        self.assertEqual(None, r.wa)
        self.assertEqual(None, r.st)
        self.assertEqual(1, procs_r)
        self.assertEqual(2, procs_b)
        self.assertEqual(2236, sys_in)
        self.assertEqual(2002, sys_cs)

    def test_parse_free(self):
        m = nm.Master()
        ctime = datetime.now()
        r = nm.parse_free('1', collect_time=ctime, content='''
                    total       used       free     shared    buffers     cached
        Mem:         19991       6428      13562          0        148       2656
        -/+ buffers/cache:       3623      16367
        Swap:        10063          0      10063
        ''')
        self.assertEqual('1', r.aid)
        self.assertEqual(ctime, r.collect_at)
        self.assertEqual(19991, r.total_mem)
        self.assertEqual(6428, r.used_mem)
        self.assertEqual(13562, r.free_mem)
        self.assertEqual(None, r.cache_mem)
        self.assertEqual(10063, r.total_swap)
        self.assertEqual(0, r.used_swap)
        self.assertEqual(10063, r.free_swap)

        r = nm.parse_free('1', collect_time=ctime, content='''
                      total        used        free      shared  buff/cache   available
        Mem:           1839         408         568          24         863        1230
        Swap:          2047           0        2047
        ''')
        self.assertEqual('1', r.aid)
        self.assertEqual(ctime, r.collect_at)
        self.assertEqual(1839, r.total_mem)
        self.assertEqual(408, r.used_mem)
        self.assertEqual(568, r.free_mem)
        self.assertEqual(None, r.cache_mem)
        self.assertEqual(2047, r.total_swap)
        self.assertEqual(0, r.used_swap)
        self.assertEqual(2047, r.free_swap)


class MasterDAOTest(BaseDBTest):

    def test_add_agent(self):
        aglist = self.dao.get_agents()
        self.assertEqual(0, len(aglist))

        ag = nm.Agent('12345678', 'agent1', '127.0.0.1', datetime.now())
        self.dao.add_agent(ag)

        aglist = self.dao.get_agents()
        self.assertEqual(1, len(aglist))
        self.assertEqual(ag, aglist[0])

    def test_update_agent(self):
        ag = nm.Agent('12345678', 'agent1', '127.0.0.1', datetime.now())
        self.dao.add_agent(ag)
        self.dao.update_agent_status(ag.aid, last_cpu_util=99, last_mem_util=55.5,
                                     last_sys_load1=1.1, last_sys_cs=123)
        aglist = self.dao.get_agents()
        self.assertEqual(1, len(aglist))
        nag = aglist[0]
        self.assertEqual(99, nag.last_cpu_util)
        self.assertEqual(55.5, nag.last_mem_util)
        self.assertEqual(1.1, nag.last_sys_load1)
        self.assertEqual(123, nag.last_sys_cs)

    def test_add_nmetrics(self):
        agentid = '12345678'
        collect_time = datetime.now()
        contents = {'w': 'content for w',
                    'vmstat': 'content for vmstat',
                    'netstat': 'content for netstat'}
        self.dao.add_nmetrics(agentid, collect_time, contents)

        nmetrics = self.dao.get_nmetrics(agentid,
                                         datetime.now() - timedelta(days=1),
                                         datetime.now() + timedelta(days=1))
        self.assertEqual(3, len(nmetrics))
        w = filter(lambda x: x.category == 'w', nmetrics)[0]
        self.assertEqual(agentid, w.aid)
        self.assertEqual(contents['w'], w.content)

    def test_add_empty_nmetrics(self):
        agentid = '12345678'
        collect_time = datetime.now()
        contents = {}
        self.dao.add_nmetrics(agentid, collect_time, contents)

        nmetrics = self.dao.get_nmetrics(agentid,
                                         datetime.now() - timedelta(days=1),
                                         datetime.now() + timedelta(days=1))
        self.assertEqual(0, len(nmetrics))

    def test_add_nmemory(self):
        mem = nm.NMemoryReport(aid='12345678', collect_at=datetime.now(),
                               total_mem=100, used_mem=50, cache_mem=10, free_mem=50,
                               total_swap=100, used_swap=20, free_swap=80)
        self.dao.add_memreport(mem)

        mems = self.dao.get_memreports('12345678',
                                       datetime.now() - timedelta(days=1),
                                       datetime.now() + timedelta(days=1))
        self.assertEqual(1, len(mems))
        self.assertEqual(mem, mems[0])

    def test_add_sysreport(self):
        sys = nm.NSystemReport(aid='123', collect_at=datetime.now(),
                               uptime=12345, users=5, load1=1, load5=5, load15=15,
                               procs_r=1, procs_b=2, sys_in=1, sys_cs=2)
        self.dao.add_sysreport(sys)
        reports = self.dao.get_sysreports('123', datetime.now() - timedelta(hours=1),
                                          datetime.now() + timedelta(hours=1))
        self.assertEqual(1, len(reports))
        self.assertEqual(sys, reports[0])

    def test_add_cpureport(self):
        cpu = nm.NCPUReport(aid='123', collect_at=datetime.now(),
                            us=2, sy=18, id=80, wa=0, st=0)
        self.dao.add_cpureport(cpu)
        cpus = self.dao.get_cpureports('123', datetime.now() - timedelta(hours=1),
                                       datetime.now() + timedelta(hours=1))
        self.assertEqual(1, len(cpus))
        self.assertEqual(cpu, cpus[0])


class MasterTest(BaseDBTest):

    def test_creation(self):
        master = nm.Master()
        self.assertEqual((socket.gethostname(), 7890), master._addr)
        self.assertEqual(5, len(master._handlers))

    def test_handle_reg(self):
        master = nm.Master()

        # test a new agent join
        regmsg = nm.Msg('1', nm.Msg.A_REG, body='''{}''')
        regmsg.client_addr = ('127.0.0.1', 1234)
        master.handle_msg(regmsg)
        agent_status = master.find_agent('1')
        self.assertEqual('1', agent_status.agent.aid)
        self.assertEqual('127.0.0.1', agent_status.agent.host)
        self.assertEqual('127.0.0.1', agent_status.agent.name)
        self.assertEqual(('127.0.0.1', 1234), agent_status.client_addr)
        self.assertTrue(agent_status.active)

        # test a agent rejoin
        agent_status.inactive()
        master.handle_msg(regmsg)
        self.assertTrue(agent_status.active)

    def test_handle_hearbeat(self):
        pass

    def test_handle_empty_nmetrics(self):
        m = nm.Master()
        ctime = datetime.now()
        body = {'collect_time': ctime}
        nmmsg = nm.Msg('2', nm.Msg.A_NODE_METRIC, body=nm.dump_json(body))
        re = m.handle_msg(nmmsg)
        self.assertTrue(re)

    def test_handle_nmetrics_linux(self):
        m = nm.Master()
        agent = nm.Agent('2', 'localhost', 'localhost', datetime.now())
        self.dao.add_agent(agent)

        ctime = datetime.now()
        msgbody = {
            'collect_time': ctime,
            'w': ''' 05:04:07 up 57 days, 10:57,  1 user,  load average: 2.11, 2.54, 2.77
                 USER     TTY      FROM             LOGIN@   IDLE   JCPU   PCPU WHAT
                 root     pts/0    pc-itian.arrs.ar 27Dec17  7.00s  1:14m  0.03s -bash
                 ''',
            'free': '''              total        used        free      shared  buff/cache   available
                    Mem:           1839         408         566          24         864        1229
                    Swap:          2047           0        2047
                    ''',
            'vmstat': '''procs -----------memory---------- ---swap-- -----io---- -system-- ------cpu-----
                         r  b   swpd   free   buff  cache   si   so    bi    bo   in   cs us sy id wa st
                         3  0      0 580284    948 884556    0    0     0     1    8    3  2  0 97  0  0
                         1  0      0 580284    948 884556    0    0     0     0 1091  404 86 14  0  0  0
                      '''
        }
        nmmsg = nm.Msg(agent.aid, nm.Msg.A_NODE_METRIC, body=nm.dump_json(msgbody))
        re = m.handle_msg(nmmsg)
        self.assertTrue(re)

        start = datetime.now() - timedelta(hours=1)
        end = datetime.now() + timedelta(hours=1)
        memreports = self.dao.get_memreports(agent.aid, start, end)
        self.assertEqual(1, len(memreports))
        self.assertEqual(nm.NMemoryReport(aid=agent.aid, collect_at=ctime,
                                          total_mem=1839, used_mem=408, free_mem=566, cache_mem=None,
                                          total_swap=2047, used_swap=0, free_swap=2047),
                         memreports[0])

        cpureports = self.dao.get_cpureports(agent.aid, start, end)
        self.assertEqual(1, len(cpureports))
        self.assertEqual(nm.NCPUReport(aid=agent.aid, collect_at=ctime, us=86, sy=14, id=0, wa=0, st=0),
                         cpureports[0])

        sysreports = self.dao.get_sysreports(agent.aid, start, end)
        self.assertEqual(1, len(sysreports))
        self.assertEqual(nm.NSystemReport(aid=agent.aid, collect_at=ctime,
                                          uptime=57*24*3600, users=1, load1=2.11, load5=2.54, load15=2.77,
                                          procs_r=1, procs_b=0, sys_in=1091, sys_cs=404),
                         sysreports[0])

        agents = self.dao.get_agents()
        self.assertEqual(1, len(agents))
        self.assertEqual(memreports[0].used_util, agents[0].last_mem_util)
        self.assertEqual(cpureports[0].used_util, agents[0].last_cpu_util)
        self.assertEqual(sysreports[0].load1, agents[0].last_sys_load1)
        self.assertEqual(sysreports[0].sys_cs, agents[0].last_sys_cs)


if __name__ == '__main__':
    unittest.main()