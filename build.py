#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Created on 2018-6-22
@author: foxty

Build scirpt for node-monitor
"""


import os, sys
import logging
import yaml
from datetime import timedelta, datetime
from subprocess import check_call, check_output, CalledProcessError

BASE_PATH = sys.path[0]
VERSION = '1.0.0-%s'
DOCKER_IMG_TAG = 'registry.cn-shenzhen.aliyuncs.com/foxty/node-monitor:%s'


def run_cmd(title, cmd):
    """
    Checking tools is valid on current platform.
    :return: True/False
    """
    t0 = datetime.now()
    ret = True
    try:
        logging.info(title)
        check_call(cmd, shell=True)
    except CalledProcessError:
        logging.error('run cmd %s failed', cmd)
        ret = False
    t1 = datetime.now()
    logging.info('%s %s, take %s seconds',
                 title,
                 'succeed' if ret else 'failed',
                 (t1 - t0).seconds)
    return ret


def build_ui():
    """
    Build ui component by using webpack and nodejs
    :return:
    """
    logging.info('[ui] build ui component')
    # step 1 install js libs
    ret = run_cmd('[ui] install javascript libs',
                  ["cd", "web", "&&", "npm", "install", "--production"])
    # step 2 webpack build
    ret = run_cmd('[ui] webpack build', ['cd', 'web', '&&', 'npm', 'run', 'build']) if ret else False

    # step 3 build docker image for UI
    # TODO
    logging.info('')
    return ret


def build_master():
    """
    Build master with Docker
    :return:
    """
    logging.info('[master] build master')
    ret = run_cmd('[master] build docker image %s' % DOCKER_IMG_TAG,
                  ['docker', 'build', '-t', DOCKER_IMG_TAG, '.'])

    ret = run_cmd('push docker image %s'% DOCKER_IMG_TAG, ['docker', 'push', DOCKER_IMG_TAG]) if ret else False
    logging.info('')
    return ret


def update_k8s_deployer():
    cfgpath = os.path.join(sys.path[0], 'deploy', 'node-monitor.yaml')
    logging.info('replace DOCKER_IMAGE_TAG in %s', cfgpath)
    cfgs = []
    with open(cfgpath) as k8scfg:
        cfg = yaml.load_all(k8scfg)
        for c in cfg:
            if c['kind'] == 'Deployment':
                c['spec']['template']['spec']['containers'][0]['image'] = DOCKER_IMG_TAG
            cfgs.append(c)
    with open(cfgpath, 'w') as k8scfg:
        yaml.dump_all(cfgs, k8scfg)
    return True


if __name__ == '__main__':
    if '--prod' in sys.argv or '--production' in sys.argv:
        VERSION = VERSION % datetime.now().strftime('%Y%m%d%H%M%S')
        DOCKER_IMG_TAG = DOCKER_IMG_TAG % VERSION
    else:
        VERSION = VERSION % 'SNAPSHOT'
        DOCKER_IMG_TAG = DOCKER_IMG_TAG % VERSION

    logging.basicConfig(level=logging.INFO)
    start = datetime.now()
    logging.info('start build node-monitor@%s...', VERSION)
    res = build_ui() and build_master() and update_k8s_deployer()
    logging.info('node-monitor@%s build %s, take %s seconds',
                 VERSION,
                 'succeed' if res else 'failed.',
                 (datetime.now() - start).seconds)

