#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Created on 2017-12-22
@author: foxty
"""

from unittest import TestCase
from agent import AgentConfig


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
        self.assertEqual(5, len(metrics))
        w = metrics['w']
        self.assertEqual(['w'], w['cmd'])
        self.assertEqual(6, w['clocks'])
        free = metrics['free']
        self.assertEqual(['free', '-m'], free['cmd'])
        self.assertEqual(6, free['clocks'])
        df = metrics['df']
        self.assertEqual(['df', '-h'], df['cmd'])
        self.assertEqual(60, df['clocks'])

    def test_service_metrics(self):
        metrics = self.CONFIG.service_metrics
        self.assertEqual(1, len(metrics))
        pidstat = metrics['pidstat']
        self.assertEqual(["pidstat", "-rtuh", "-p", "${pid}"], pidstat['cmd'])
        self.assertEqual(6, pidstat['clocks'])
