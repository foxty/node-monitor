#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Created on 2017-12-22
@author: foxty
"""

from unittest import TestCase
from agent import AgentConfig, NodeCollector


class AgentConfigTest(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.CONFIG = AgentConfig('../nodemonitor/agent.json')

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
        self.assertEqual(["pidstat", "-rtuh", "-p", "${pid}"], pidstat['cmd'])


class NodeCollectorTest(TestCase):

    @classmethod
    def setUpClass(cls):

        class MockAgent(object):
            def __init__(self):
                self.agentid = '1'

        cls.COLLECTOR = NodeCollector(MockAgent(), AgentConfig('../nodemonitor/agent.json'))

    def test_trans_cmd(self):
        cmd = ['test1', '${var1}', 'and${var2}']
        context = {'var1': '1', 'var2': '2'}
        newcmd = self.COLLECTOR._translate_cmd(cmd, context)
        self.assertEqual(['test1', '1', 'and2'], newcmd)

