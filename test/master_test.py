#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Created on 2017-12-22
@author: foxty
"""

import unittest
import time
import model
import model_test
from datetime import datetime, timedelta
from common import Msg
from master import Master, DataKeeper



class MasterTest(model_test.BaseDBTest):
    def setUp(self):
        model_test.BaseDBTest.setUp(self)
        config = {
            'master': {
                'server': {
                    'host': '0.0.0.0',
                    'port': 7890
                },
                'data_retention': {
                    'interval': 10,
                    'policy': {}
                }
            }
        }
        self.master = Master(config)

    def test_creation(self):
        master = self.master
        self.assertEqual(('0.0.0.0', 7890), master._agent_manager._server_addr)
        self.assertEqual(4, len(master._handlers))

    def test_handle_reg(self):
        master = self.master

        # test a new agent join
        regmsg = Msg.create_msg('1', Msg.A_REG, {'os': 'LINUX', 'hostname': 'test-host'})
        agent_addr = ('localhost', 12345)

        master.handle_msg(regmsg, agent_addr)
        agent = master.find_agent('1')
        self.assertEqual('1', agent.aid)
        self.assertEqual('test-host', agent.host)
        self.assertEqual('test-host@LINUX', agent.name)

    def test_handle_hearbeat(self):
        pass

    def test_handle_empty_nmetrics(self):
        m = self.master
        ctime = datetime.now()
        body = {'collect_time': ctime}
        regmsg = Msg.create_msg('2', Msg.A_REG, {'os': 'LINUX', 'hostname': 'test-host'})
        agent_addr = ('localhost', 12345)
        m.handle_msg(regmsg, agent_addr)

        nmmsg = Msg.create_msg('2', Msg.A_NODE_METRIC, body)
        re = m.handle_msg(nmmsg, agent_addr)
        self.assertTrue(re)

    def test_handle_nmetrics_linux(self):
        agent = model.Agent('2', 'localhost', 'localhost', datetime.now())
        agent.save()

        m = self.master
        m._load_agents()
        ctime = datetime.now()
        agent_addr = ('localhost', 12345)
        msgbody = {
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
        nmmsg = Msg.create_msg(agent.aid, Msg.A_NODE_METRIC, msgbody)
        nmmsg.set_header(nmmsg.H_COLLECT_AT, ctime)
        re = m.handle_msg(nmmsg, agent_addr)
        self.assertTrue(re)
        agents = model.Agent.query()
        self.assertEqual(1, len(agents))

    def test_handle_smetrics(self):
        aid = '2'
        agent = model.Agent(aid, 'localhost', 'localhost', datetime.now())
        agent.save()

        m = self.master
        ctime = datetime.now()
        agent_addr = ('localhost', 12345)
        msgbody = {'name': 'service1', 'pid': '1', 'metrics': {'m1': 'm1 content', 'm2': 'm2 content'}}
        nmmsg = Msg.create_msg(agent.aid, Msg.A_SERVICE_METRIC, msgbody)
        nmmsg.set_header(Msg.H_COLLECT_AT, ctime)
        re = m.handle_msg(nmmsg, agent_addr)
        self.assertTrue(re)

        smetrics = model.SMetric.query(orderby='category ASC')
        self.assertEqual(2, len(smetrics))
        sm1, sm2 = smetrics[0], smetrics[1]
        self.assertEqual(aid, sm1.aid)
        self.assertEqual(ctime.replace(microsecond=0), sm1.collect_at)
        self.assertEqual('service1', sm1.name)
        self.assertEqual(1, sm1.pid)
        self.assertEqual('m1', sm1.category)
        self.assertEqual('m1 content', sm1.content)

        sinfo = model.SInfo.query_by_aid(aid)[0]
        self.assertEqual(aid, sinfo.aid)
        self.assertEqual('service1', sinfo.name)
        self.assertEqual(1, sinfo.pid)
        self.assertEqual(ctime.replace(microsecond=0), sinfo.last_report_at)
        self.assertEqual(model.SInfo.STATUS_ACT, sinfo.status.strip())

    def test_handle_smetrics_pidchg(self):
        aid = '2'
        agent = model.Agent(aid, 'localhost', 'localhost', datetime.now())
        agent.save()

        m = self.master
        ctime = datetime.now()
        agent_addr = ('localhost', 12345)
        msgbody = {'name': 'service1', 'pid': '1', 'metrics': {'m1': 'm1 content', 'm2': 'm2 content'}}
        nmmsg = Msg.create_msg(agent.aid, Msg.A_SERVICE_METRIC, msgbody)
        nmmsg.set_header(Msg.H_COLLECT_AT, ctime)
        m.handle_msg(nmmsg, agent_addr)

        ctime1 = datetime.now() + timedelta(hours=1)
        msgbody['pid'] = '2'
        nmmsg = Msg.create_msg(agent.aid, Msg.A_SERVICE_METRIC, msgbody)
        nmmsg.set_header(Msg.H_COLLECT_AT, ctime1)
        m.handle_msg(nmmsg, agent_addr)

        smetrics = model.SMetric.query()
        self.assertEqual(4, len(smetrics))

        sinfo = model.SInfo.query_by_aid(aid)[0]
        self.assertEqual(aid, sinfo.aid)
        self.assertEqual('service1', sinfo.name)
        self.assertEqual(2, sinfo.pid)
        self.assertEqual(ctime1.replace(microsecond=0), sinfo.last_report_at)
        self.assertEqual(model.SInfo.STATUS_ACT, sinfo.status.strip())

        sinfohis = model.SInfoHistory.query(orderby='recv_at ASC')
        self.assertEqual(2, len(sinfohis))
        self.assertEqual(1, sinfohis[0].pid)
        self.assertEqual(2, sinfohis[1].pid)


class DataKeeperTest(model_test.BaseDBTest):

    def setUp(self):
        model_test.BaseDBTest.setUp(self)
        config = {
            'interval': 3,
            'policy': {
                'node_metric_raw': 5
            }
        }
        self.data_keeper = DataKeeper(config)

    def test_init(self):
        dk = self.data_keeper
        self.assertEqual(3, dk._interval)
        self.assertEqual({'node_metric_raw': 5}, dk._policy)
        self.assertEqual(0, dk._count)
        self.assertFalse(dk._run)
        self.assertEqual(None, dk._startat)
        self.assertEqual(None, dk._timer)

    def test_start_stop(self):
        dk = self.data_keeper
        dk.start()
        self.assertTrue(dk._run)
        self.assertIsNotNone(dk._timer)
        self.assertIsNotNone(dk._startat)
        time.sleep(dk._interval + 1)
        dk.stop()
        self.assertFalse(dk._run)
        self.assertEqual(1, dk._count)


if __name__ == '__main__':
    unittest.main()