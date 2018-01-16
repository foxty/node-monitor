#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Created on 2017-12-22
@author: foxty
"""

import unittest
import base64
import os
import socket
import node_monitor as nm
from datetime import datetime, date, time, timedelta

nm._MASTER_DB_NAME = 'test.db'


class BaseDBTest(unittest.TestCase):
    def setUp(self):
        if os.path.exists(nm._MASTER_DB_NAME):
            os.remove(nm._MASTER_DB_NAME)
        self.dao = nm.MasterDAO()

    def tearDown(self):
        if os.path.exists(nm._MASTER_DB_NAME):
            os.remove(nm._MASTER_DB_NAME)


class GlobalFuncTest(unittest.TestCase):

    def test_dumpjson(self):
        dt = datetime(2018, 1, 8, 17, 26, 26, 999)
        json_dt = nm.dump_json(dt)
        self.assertEqual('"2018-01-08 17:26:26.000999"', json_dt)

        d = dt.date()
        json_d = nm.dump_json(d)
        self.assertEqual('"2018-01-08"', json_d)

        t = dt.time()
        json_t = nm.dump_json(t)
        self.assertEqual('"17:26:26.000999"', json_t)

    def test_loadjson(self):
        json_dt = '{"date":"2018-01-08 17:26:26.000999", ' \
                  '"entry1":{"start_dt":"2018-01-08 17:26:27.999000", "d":"2018-01-01", "t":"01:01:01:100"}}'
        dt = nm.load_json(json_dt)
        self.assertEqual('2018-01-08 17:26:26.000999', dt['date'].strftime(nm._DATETIME_FMT))
        self.assertEqual('2018-01-01', dt['entry1']['d'].strftime(nm._DATE_FMT))

        def test_parse_w_linux(self):
            m = nm.Master()
        ctime = datetime.now()
        r = nm.parse_w('1', collect_time=ctime, content='''
         21:25:14 up 45 days,  3:18,  12 user,  load average: 10.00, 10.03, 10.05
        USER     TTY      FROM             LOGIN@   IDLE   JCPU   PCPU WHAT
        root     pts/0    pc-itian.arrs.ar 27Dec17  2.00s  8:47   0.00s w
        ''')
        self.assertEqual('1', r.aid)
        self.assertEqual(ctime, r.collect_at)
        self.assertEqual(45*24*3600, r.uptime)
        self.assertEqual(12, r.users)
        self.assertEqual(10.00, r.load1)
        self.assertEqual(10.03, r.load5)
        self.assertEqual(10.05, r.load15)
        self.assertIsNone(r.procs_r)
        self.assertIsNone(r.procs_b)
        self.assertIsNone(r.sys_in)
        self.assertIsNone(r.sys_cs)

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


class TextTableTest(unittest.TestCase):

    _TABLE = '''
        A   b   c   d   e   f    g   g
        a1  b1  c1  d1  e1  f1   g1  g2
    1   2   3   4   5   6    7  77
        1.1  2.2  3.3  4.4  5.5  6.6  7.7 77.77
        '''

    def test_creation(self):
        t = nm.TextTable(self._TABLE)

        self.assertEqual(4, t.size)
        self.assertEqual(8, len(t._hheader))
        self.assertEqual('Abcdefgg', ''.join(t._hheader))

        t = nm.TextTable(self._TABLE, 1)

        self.assertEqual(4, t.size)
        self.assertEqual(8, len(t._hheader))
        self.assertEqual('a1b1c1d1e1f1g1g2', ''.join(t._hheader))

    def test_gets(self):
        t = nm.TextTable(self._TABLE)
        self.assertEqual('a1', t.get(1, 'A'))
        self.assertEqual('b1', t.get(1, 'b'))
        self.assertEqual('g1', t.get(1, 'g'))
        self.assertEqual(['g1', 'g2'], t.gets(1, 'g'))
        self.assertIsNone(t.get(1, 'non-exist'))
        self.assertEqual('aa', t.get(1, 'non-exist', 'aa'))

        self.assertEqual(1, t.get_int(2, 'A'))
        self.assertEqual(2, t.get_int(2, 'b'))
        self.assertEqual(7, t.get_int(2, 'g'))
        self.assertEqual([7, 77], t.get_ints(2, 'g'))
        self.assertIsNone(t.get(2, 'non-exist'))
        self.assertEqual(8, t.get(2, 'non-exist', 8))

        self.assertEqual(1.1, t.get_float(3, 'A'))
        self.assertEqual(2.2, t.get_float(3, 'b'))
        self.assertEqual(7.7, t.get_float(3, 'g'))
        self.assertEqual([7.7, 77.77], t.get_floats(3, 'g'))
        self.assertIsNone(t.get(3, 'non-exist'))
        self.assertEqual(8.8, t.get(2, 'non-exist', 8.8))


class MonMsgTest(unittest.TestCase):

    def test_create(self):
        m1 = nm.Msg("12345678")
        self.assertEqual("12345678", m1.agentid)
        self.assertEqual(nm.Msg.NONE, m1.msg_type)
        self.assertEqual('', m1.body)

    def test_eq(self):
        m1 = nm.Msg("12345678")
        m2 = nm.Msg("12345678")
        self.assertEqual(m1, m2)

        m2.msg_type = nm.Msg.A_HEARTBEAT
        self.assertNotEqual(m1, m2)

        m1.msg_type = nm.Msg.A_HEARTBEAT
        self.assertEqual(m1, m2)

        m1.body = "123"
        self.assertNotEqual(m1, m2)

    def test_encode_decode(self):
        msg_body = "12\n\t\n\t34"
        msg = nm.Msg("12345678", nm.Msg.A_HEARTBEAT, body=msg_body)
        self.assertEqual(nm.Msg.A_HEARTBEAT, msg.msg_type)

        header_list, encbody = msg.encode()
        self.assertEqual(4, len(header_list))
        self.assertEqual(msg_body, base64.b64decode(encbody))

        msg1 = nm.Msg.decode(header_list, encbody)
        self.assertEqual(msg, msg1)
        self.assertEqual(msg.sendtime, msg1.sendtime)
        self.assertEqual(True, isinstance(msg.sendtime, datetime))


class MasterDAOTest(BaseDBTest):

    def test_add_agent(self):
        aglist = self.dao.get_agents()
        self.assertEqual(0, len(aglist))

        ag = nm.Agent('12345678', 'agent1', '127.0.0.1', datetime.now())
        self.dao.add_agent(ag)

        aglist = self.dao.get_agents()
        self.assertEqual(1, len(aglist))
        self.assertEqual(ag, aglist[0])

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
        aid = '2'
        m = nm.Master()
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
        nmmsg = nm.Msg(aid, nm.Msg.A_NODE_METRIC, body=nm.dump_json(msgbody))
        re = m.handle_msg(nmmsg)
        self.assertTrue(re)

        start = datetime.now() - timedelta(hours=1)
        end = datetime.now() + timedelta(hours=1)
        memreports = self.dao.get_memreports(aid, start, end)
        self.assertEqual(1, len(memreports))
        self.assertEqual(nm.NMemoryReport(aid=aid, collect_at=ctime,
                                          total_mem=1839, used_mem=408, free_mem=566, cache_mem=None,
                                          total_swap=2047, used_swap=0, free_swap=2047),
                         memreports[0])

        cpureports = self.dao.get_cpureports(aid, start, end)
        self.assertEqual(1, len(cpureports))
        self.assertEqual(nm.NCPUReport(aid=aid, collect_at=ctime, us=86, sy=14, id=0, wa=0, st=0),
                         cpureports[0])

        sysreports = self.dao.get_sysreports(aid, start, end)
        self.assertEqual(1, len(sysreports))
        self.assertEqual(nm.NSystemReport(aid=aid, collect_at=ctime,
                                          uptime=57*24*3600, users=1, load1=2.11, load5=2.54, load15=2.77,
                                          procs_r=1, procs_b=0, sys_in=1091, sys_cs=404),
                         sysreports[0])


if __name__ == '__main__':
    unittest.main()