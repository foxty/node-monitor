#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Created on 2017-12-22
@author: foxty
"""

import unittest
import subprocess
import json
from mock import MagicMock, patch
from common import Msg
from agent import AgentConfig, NodeCollector


class AgentConfigTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.CONFIG = AgentConfig('agent_test.json')

    def test_clock_interval(self):
        self.assertEqual(10, self.CONFIG.clock_interval)

    def test_hb_clocks(self):
        self.assertEqual(6, self.CONFIG.hb_clocks)

    def test_node_metrics(self):
        metrics = self.CONFIG.node_metrics
        self.assertEqual(10, len(metrics))
        w = metrics['w']
        self.assertEqual(['w'], w['cmd'])
        self.assertEqual(6, w['clocks'])
        free = metrics['free']
        self.assertEqual(['free', '-m'], free['cmd'])
        self.assertEqual(6, free['clocks'])
        df = metrics['df']
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

        class MockAgentConfig(object):
            def __init__(self, cfgpath):
                with open(cfgpath) as f:
                    self.config = json.load(f)

            @property
            def valid_node_metrics(self):
                return self.config['node_metrics']

            @property
            def valid_services(self):
                return self.config['services']

            @property
            def clock_interval(self):
                return self.config['clock_interval']

        cls.AGENT = MockAgent()
        cls.COLLECTOR = NodeCollector(cls.AGENT, MockAgentConfig('agent_test.json'))
        cls.COLLECTOR._get_cmd_result = MagicMock(return_value='cmd content')

    def test_trans_cmd(self):
        cmd = ['test1', '${var1}', 'and${var2}']
        context = {'var1': '1', 'var2': '2'}
        newcmd = self.COLLECTOR._translate_cmd(cmd, context)
        self.assertEqual(['test1', '1', 'and2'], newcmd)

    def test_prod_heartbeat(self):
        self.COLLECTOR._prod_heartbeat()
        hbmsg = self.AGENT.msg
        msgbody = json.loads(hbmsg.body)
        self.assertEqual(Msg.A_HEARTBEAT, hbmsg.msg_type)
        self.assertEqual('1', hbmsg.agentid)
        self.assertTrue('datetime' in msgbody)

    def test_collect_nmetrics(self):
        self.COLLECTOR._collect_nmetrics(1)
        self.assertIsNone(self.AGENT.msg)

        self.COLLECTOR._collect_nmetrics(6)
        msg = self.AGENT.msg
        msgbody = json.loads(msg.body)
        self.assertIsNotNone(msg)
        self.assertEqual('1', msg.agentid)
        self.assertEqual(Msg.A_NODE_METRIC, msg.msg_type)
        self.assertEqual(9, len(msgbody))
        self.assertEqual('cmd content', msgbody['w'])
        self.assertEqual('cmd content', msgbody['free'])
        self.assertEqual('cmd content', msgbody['vmstat'])

        self.COLLECTOR._collect_nmetrics(60)
        msg = self.AGENT.msg
        msgbody = json.loads(msg.body)
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