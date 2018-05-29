#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Created on 2017-12-22
@author: foxty
"""

import unittest
from mock import MagicMock
from common import Msg, ostype, is_linux, is_sunos, is_win, OSType
from agent import AgentConfig, NodeCollector, is_metric_valid


class GlobalTest(unittest.TestCase):

    def test_is_metric_valid(self):
        os = OSType.WIN
        if is_linux():
            os = OSType.LINUX
        elif is_win():
            os = OSType.WIN
        elif is_sunos():
            os = OSType.SUNOS
        metric = {'name': 'cd', 'cmd': ['ls', '/'], 'os': os}
        re = is_metric_valid(metric)
        self.assertTrue(re)


class AgentConfigTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.CONFIG = AgentConfig()

    def test_clock_interval(self):
        self.assertEqual(10, self.CONFIG.clock_interval)

    def test_hb_clocks(self):
        self.assertEqual(6, self.CONFIG.hb_clocks)

    def test_node_metrics(self):
        metrics = self.CONFIG.node_metrics
        self.assertEqual(11, len(metrics))
        w = metrics[5]
        self.assertEqual(['w'], w['cmd'])
        self.assertEqual(6, w['clocks'])
        free = metrics[6]
        self.assertEqual(['free', '-m'], free['cmd'])
        self.assertEqual(6, free['clocks'])
        df = metrics[9]
        self.assertEqual(['df', '-k'], df['cmd'])
        self.assertEqual(60, df['clocks'])
        df = metrics[10]
        self.assertEqual(['df', '-kP'], df['cmd'])
        self.assertEqual(60, df['clocks'])

    def test_service_metrics(self):
        metrics = self.CONFIG.service_metrics
        self.assertEqual(2, len(metrics))
        pidstat = metrics['pidstat']
        self.assertEqual(["pidstat", "-tdruh", "-p", "${pid}"], pidstat['cmd'])


class NodeCollectorTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):

        class MockAgent(object):
            def __init__(self):
                self.agentid = '1'
                self.msg = None

            def add_msg(self, msg):
                self.msg = msg

        class MockAgentConfig(AgentConfig):

            @property
            def valid_node_metrics(self):
                return self.CONFIG['node_metrics']

            @property
            def valid_services(self):
                return self.CONFIG['services']

            @property
            def clock_interval(self):
                return self.CONFIG['clock_interval']

        cls.AGENT = MockAgent()
        cls.COLLECTOR = NodeCollector(cls.AGENT, MockAgentConfig())
        cls.COLLECTOR._get_cmd_result = MagicMock(return_value='cmd content')

    def test_trans_cmd(self):
        cmd = ['test1', '${var1}', 'and${var2}-${var3}']
        context = {'var1': '1', 'var2': '2', 'var3':'3'}
        newcmd = self.COLLECTOR._translate_cmd(cmd, context)
        self.assertEqual(['test1', '1', 'and2-3'], newcmd)

    def test_prod_heartbeat(self):
        self.COLLECTOR._prod_heartbeat()
        hbmsg = self.AGENT.msg
        msgbody = hbmsg.body
        self.assertEqual(Msg.A_HEARTBEAT, hbmsg.msg_type)
        self.assertEqual('1', hbmsg.agentid)
        self.assertTrue('datetime' in msgbody)

    def test_collect_nmetrics(self):
        self.COLLECTOR._collect_nmetrics(1)
        self.assertIsNone(self.AGENT.msg)

        self.COLLECTOR._collect_nmetrics(6)
        msg = self.AGENT.msg
        msgbody = msg.body
        self.assertIsNotNone(msg)
        self.assertEqual('1', msg.agentid)
        self.assertEqual(Msg.A_NODE_METRIC, msg.msg_type)
        self.assertEqual(9, len(msgbody))
        self.assertEqual('cmd content', msgbody['w'])
        self.assertEqual('cmd content', msgbody['free'])
        self.assertEqual('cmd content', msgbody['vmstat'])

        self.COLLECTOR._collect_nmetrics(60)
        msg = self.AGENT.msg
        msgbody = msg.body
        self.assertIsNotNone(msg)
        self.assertEqual('1', msg.agentid)
        self.assertEqual(msg.A_NODE_METRIC, msg.msg_type)
        self.assertEqual(10, len(msgbody))
        self.assertEqual('cmd content', msgbody['df'])

    def test_collect_smetrics(self):
        pass


class AgentTest(unittest.TestCase):
    pass


if __name__ == '__main__':
    unittest.main()