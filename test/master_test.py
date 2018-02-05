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
        nm.create_schema()

    def tearDown(self):
        if os.path.exists(nm._MASTER_DB_NAME):
            os.remove(nm._MASTER_DB_NAME)


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
        ctime = datetime.now()
        r = nm.parse_w('2', collect_time=ctime, content='''
        9:11pm  up 43 day(s),  8:52,  11 user,  load average: 2.38, 2.41, 2.41
        User     tty           login@  idle   JCPU   PCPU  what
        root     pts/4        27Dec17           18         -bash
        ''')
        self.assertEqual('2', r.aid)
        self.assertEqual(ctime, r.collect_at)
        self.assertEqual(0, r.uptime)
        self.assertEqual(11, r.users)
        self.assertEqual(2.38, r.load1)
        self.assertEqual(2.41, r.load5)
        self.assertEqual(2.41, r.load15)
        self.assertIsNone(r.procs_r)
        self.assertIsNone(r.procs_b)
        self.assertIsNone(r.sys_in)
        self.assertIsNone(r.sys_cs)
        self.assertIsNotNone(r.recv_at)

    def test_parse_w_linux(self):
        ctime = datetime.now()
        r = nm.parse_w('2', collect_time=ctime, content='''
        21:26:13 up  3:32,  3 users,  load average: 0.00, 0.03, 0.00
        USER     TTY      FROM              LOGIN@   IDLE   JCPU   PCPU WHAT
        root     pts/2    pc-llou.arrs.arr 17:53    3:32m  0.00s  0.00s -bash
        root     pts/1    pc-yzhang3.arrs. 17:53    3:32m  0.00s  0.00s -bash
        root     pts/0    pc-itian.arrs.ar 21:20    3:18   0.01s  0.01s -bash
        ''')
        self.assertEqual('2', r.aid)
        self.assertEqual(ctime, r.collect_at)
        self.assertEqual(0, r.uptime)
        self.assertEqual(3, r.users)
        self.assertEqual(0.00, r.load1)
        self.assertEqual(0.03, r.load5)
        self.assertEqual(0.00, r.load15)
        self.assertIsNone(r.procs_r)
        self.assertIsNone(r.procs_b)
        self.assertIsNone(r.sys_in)
        self.assertIsNone(r.sys_cs)
        self.assertIsNotNone(r.recv_at)

    def test_parse_vmstat_linux(self):
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
        self.assertIsNotNone(r.recv_at)

    def test_parse_vmstat_solaris(self):
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
        self.assertIsNotNone(r.recv_at)

    def test_parse_free(self):
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
        self.assertIsNotNone(r.recv_at)

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
        self.assertIsNotNone(r.recv_at)

    def _assert_dr(self, aid, ctime, fs, size, used, avai, used_util, mount, dr):
        self.assertEqual(aid, dr.aid)
        self.assertEqual(ctime, dr.collect_at)
        self.assertEqual(fs, dr.fs)
        self.assertEqual(size, dr.size)
        self.assertEqual(used, dr.used)
        self.assertEqual(avai, dr.available)
        self.assertEqual(used_util, dr.used_util)
        self.assertEqual(mount, dr.mount_point)
        self.assertIsNotNone(dr.recv_at)

    def test_parse_df_linux(self):
        content = '''
        Filesystem          1K-blocks    Used Available Use% Mounted on
        /dev/mapper/cl-root  52403200 3294392  49108808   7% /
        devtmpfs               931344       0    931344   0% /dev
        tmpfs                  942056       0    942056   0% /dev/shm
        tmpfs                  942056   25116    916940   3% /run
        tmpfs                  942056       0    942056   0% /sys/fs/cgroup
        /dev/mapper/cl-home 112134660   32944 112101716   1% /home
        /dev/sda1             1038336  187756    850580  19% /boot
        tmpfs                  188412       0    188412   0% /run/user/0
        '''
        ctime = datetime.now()
        drs = nm.parse_df('1', collect_time=ctime, content=content)
        self.assertEqual(8, len(drs))
        self._assert_dr('1', ctime, '/dev/mapper/cl-root', '52403200', '3294392', '49108808', '7%', '/', drs[0])
        self._assert_dr('1', ctime, 'tmpfs', '188412', '0', '188412', '0%', '/run/user/0', drs[-1])

    def test_parse_df_solaris(self):
        content = '''
        Filesystem            kbytes    used   avail capacity  Mounted on
        /                    369884093 25200224 344683869     7%    /
        /dev                 369884093 25200224 344683869     7%    /dev
        /lib                 842900159 4687993 838212166     1%    /lib
        /platform            842900159 4687993 838212166     1%    /platform
        /sbin                842900159 4687993 838212166     1%    /sbin
        proc                       0       0       0     0%    /proc
        ctfs                       0       0       0     0%    /system/contract
        mnttab                     0       0       0     0%    /etc/mnttab
        objfs                      0       0       0     0%    /system/object
        swap                 1326612     344 1326268     1%    /etc/svc/volatile
        /usr/lib/libc/libc_hwcap1.so.1 369884093 25200224 344683869     7%    /lib/libc.so.1
        fd                         0       0       0     0%    /dev/fd
        swap                 1326624     356 1326268     1%    /tmp
        swap                 1326292      24 1326268     1%    /var/run

        '''
        ctime = datetime.now()
        drs = nm.parse_df('1', collect_time=ctime, content=content)
        self.assertEqual(14, len(drs))
        self._assert_dr('1', ctime, '/', '369884093', '25200224', '344683869', '7%', '/', drs[0])
        self._assert_dr('1', ctime, 'swap', '1326292', '24', '1326268', '1%', '/var/run', drs[-1])


class ModelTest(unittest.TestCase):

    class ModelA(nm.Model):
        FIELDS = ['a1', 'a2', 'a3']

    def test_model(self):
        m = ModelTest.ModelA()
        self.assertIsNone(m.a1)

    def test_model_invalidfield(self):
        with self.assertRaises(nm.InvalidFieldError) as cm:
            ModelTest.ModelA(a4=1)
            self.assertEqual('a4', cm.exception.msg)
        with self.assertRaises(nm.InvalidFieldError) as cm:
            ModelTest.ModelA().non_exist_field1
            self.assertEqual('field a non_exist_field1 not defined.', cm.exception.msg)
        with self.assertRaises(nm.InvalidFieldError) as cm:
            ModelTest.ModelA().non_exist_field2 = 1
            self.assertEqual('field a non_exist_field2 not defined.', cm.exception.msg)


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


class MasterDAOTest(BaseDBTest):

    def test_add_agent(self):
        aglist = nm.Agent.query()
        self.assertEqual(0, len(aglist))

        ag = nm.Agent('12345678', 'agent1', '127.0.0.1', datetime.now())
        ag.save()

        aglist = nm.Agent.query()
        self.assertEqual(1, len(aglist))
        self.assertEqual(ag, aglist[0])

    def test_agent_query(self):
        ag1 = nm.Agent('1', 'agent1', '127.0.0.1', datetime.now())
        ag1.save()
        ag2 = nm.Agent('2', 'agent2', '127.0.0.1', datetime.now())
        ag2.save()

        agents = nm.Agent.query()
        self.assertEqual(2, len(agents))

        agents = nm.Agent.query(where='aid=?', params=['1'])
        self.assertEqual(1, len(agents))
        self.assertEqual(ag1, agents[0])

        agents = nm.Agent.query(orderby='aid ASC')
        self.assertEqual(2, len(agents))
        self.assertEqual(ag1, agents[0])
        self.assertEqual(ag2, agents[1])

    def test_update_agent(self):
        ag = nm.Agent('12345678', 'agent1', '127.0.0.1', datetime.now())
        ag.save()
        ag.set(last_cpu_util=99, last_mem_util=55.5, last_sys_load1=1.1, last_sys_cs=123)
        aglist = nm.Agent.query()
        self.assertEqual(1, len(aglist))
        nag = aglist[0]
        self.assertEqual(99, nag.last_cpu_util)
        self.assertEqual(55.5, nag.last_mem_util)
        self.assertEqual(1.1, nag.last_sys_load1)
        self.assertEqual(123, nag.last_sys_cs)

    def test_add_nmemory(self):
        mem = nm.NMemoryReport(aid='12345678', collect_at=datetime.now(),
                               total_mem=100, used_mem=50, cache_mem=10, free_mem=50,
                               total_swap=100, used_swap=20, free_swap=80)
        mem.save()

        mems = nm.NMemoryReport.query_by_ctime('12345678',
                                               datetime.now() - timedelta(days=1),
                                               datetime.now() + timedelta(days=1))
        self.assertEqual(1, len(mems))
        self.assertEqual(mem, mems[0])

    def test_add_sysreport(self):
        sys = nm.NSystemReport(aid='123', collect_at=datetime.now(),
                               uptime=12345, users=5, load1=1, load5=5, load15=15,
                               procs_r=1, procs_b=2, sys_in=1, sys_cs=2)
        sys.save()
        reports = nm.NSystemReport.query_by_ctime('123', datetime.now() - timedelta(hours=1),
                                                  datetime.now() + timedelta(hours=1))
        self.assertEqual(1, len(reports))
        self.assertEqual(sys, reports[0])

    def test_add_cpureport(self):
        cpu = nm.NCPUReport(aid='123', collect_at=datetime.now(),
                            us=2, sy=18, id=80, wa=0, st=0)
        cpu.save()
        cpus = nm.NCPUReport.query_by_ctime('123', datetime.now() - timedelta(hours=1),
                                            datetime.now() + timedelta(hours=1))
        self.assertEqual(1, len(cpus))
        self.assertEqual(cpu, cpus[0])

    def test_cpu_chrono(self):
        now = datetime.now()
        prev_hour = now - timedelta(hours=1)
        cpu1 = nm.NCPUReport(aid='123', collect_at=prev_hour, us=1, recv_at=now)
        cpu1.save()
        cpu2 = nm.NCPUReport(aid='123', collect_at=now, us=2, recv_at=prev_hour)
        cpu2. save()

        cpus = nm.NCPUReport.query()
        self.assertEqual(2, len(cpus))

        cpus = nm.NCPUReport.query_by_ctime('123', start=prev_hour-timedelta(minutes=30), end=prev_hour+timedelta(minutes=30))
        self.assertEqual(1, len(cpus))
        self.assertEqual(cpu1, cpus[0])

        cpus = nm.NCPUReport.query_by_rtime('123', start=now-timedelta(minutes=30), end=now+timedelta(minutes=30))
        self.assertEqual(1, len(cpus))
        self.assertEqual(cpu1, cpus[0])

    def test_add_diskreports(self):
        dr1 = nm.NDiskReport(aid='123', collect_at=datetime.now(),
                             fs="/", size=1024, used=256, available=768, used_util='25%', mount_point="/root")
        dr2 = nm.NDiskReport(aid='123', collect_at=datetime.now(),
                             fs="/abc", size=1024, used=256, available=768, used_util='25%', mount_point="/var")
        drs = [dr1, dr2]
        nm.NDiskReport.save_all(drs)
        reports = nm.NDiskReport.query_by_ctime('123', datetime.now() - timedelta(hours=1),
                                                datetime.now() + timedelta(hours=1))
        self.assertEqual(2, len(reports))
        self.assertEqual(dr1, reports[0])
        self.assertEqual(dr2, reports[1])


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
        master.handle_msg(regmsg, None)
        agent = master.find_agent('1')
        self.assertEqual('1', agent.aid)
        self.assertEqual('127.0.0.1', agent.host)
        self.assertEqual('127.0.0.1', agent.name)

    def test_handle_hearbeat(self):
        pass

    def test_handle_empty_nmetrics(self):
        m = nm.Master()
        ctime = datetime.now()
        body = {'collect_time': ctime}
        regmsg = nm.Msg('2', nm.Msg.A_REG, body='''{}''')
        regmsg.client_addr = ('127.0.0.1', 1234)
        m.handle_msg(regmsg, None)

        nmmsg = nm.Msg('2', nm.Msg.A_NODE_METRIC, body=nm.dump_json(body))
        re = m.handle_msg(nmmsg, None)
        self.assertTrue(re)

    def test_handle_nmetrics_linux(self):
        agent = nm.Agent('2', 'localhost', 'localhost', datetime.now())
        agent.save()

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
        nmmsg = nm.Msg(agent.aid, nm.Msg.A_NODE_METRIC, body=nm.dump_json(msgbody))
        re = m.handle_msg(nmmsg, None)
        self.assertTrue(re)

        start = datetime.now() - timedelta(hours=1)
        end = datetime.now() + timedelta(hours=1)
        memreports = nm.NMemoryReport.query_by_ctime(agent.aid, start, end)
        self.assertEqual(1, len(memreports))
        self.assertIsNotNone(memreports[0].recv_at)
        del memreports[0]['recv_at']
        self.assertEqual(nm.NMemoryReport(aid=agent.aid, collect_at=ctime,
                                          total_mem=1839, used_mem=408, free_mem=566, cache_mem=None,
                                          total_swap=2047, used_swap=0, free_swap=2047),
                         memreports[0])

        cpureports = nm.NCPUReport.query_by_ctime(agent.aid, start, end)
        self.assertEqual(1, len(cpureports))
        self.assertIsNotNone(cpureports[0].recv_at)
        del cpureports[0]['recv_at']
        self.assertEqual(nm.NCPUReport(aid=agent.aid, collect_at=ctime, us=86, sy=14, id=0, wa=0, st=0),
                         cpureports[0])

        sysreports = nm.NSystemReport.query_by_ctime(agent.aid, start, end)
        self.assertEqual(1, len(sysreports))
        self.assertIsNotNone(sysreports[0].recv_at)
        del sysreports[0]['recv_at']
        self.assertEqual(nm.NSystemReport(aid=agent.aid, collect_at=ctime,
                                          uptime=0, users=1, load1=2.11, load5=2.54, load15=2.77,
                                          procs_r=1, procs_b=0, sys_in=1091, sys_cs=404),
                         sysreports[0])

        agents = nm.Agent.query()
        self.assertEqual(1, len(agents))
        self.assertEqual(memreports[0].used_util, agents[0].last_mem_util)
        self.assertEqual(cpureports[0].used_util, agents[0].last_cpu_util)
        self.assertEqual(sysreports[0].load1, agents[0].last_sys_load1)
        self.assertEqual(sysreports[0].sys_cs, agents[0].last_sys_cs)


if __name__ == '__main__':
    unittest.main()