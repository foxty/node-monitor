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
MASTER_DOCKER_IMG_TAG = 'foxty/node-monitor-master'
REPORT_UI_DOCKER_IMG_TAG = 'foxty/node-monitor-reportui'


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
    Build ui base on grafana
    :return:
    """
    logging.info('[ui] build report ui ')
    tag = REPORT_UI_DOCKER_IMG_TAG + ':' + VERSION
    ret = run_cmd('[ui] build docker image %s' % tag,
                  ['docker', 'build', '-f', os.path.join('docker', 'Dockerfile.ReportUI'), '-t', tag, '.'])
    logging.info('')
    return ret


def build_master():
    """
    Build master with Docker
    :return:
    """
    tag = MASTER_DOCKER_IMG_TAG + ':' + VERSION
    # build master images
    # step 1 install js libs
    ret = run_cmd('[master] install javascript libs',
                  ["cd", "web", "&&", "npm", "install", "--production"])
    # step 2 webpack build
    ret = run_cmd('[master] webpack build', ['cd', 'web', '&&', 'npm', 'run', 'build']) if ret else False

    logging.info('[master] build master')
    ret = run_cmd('[master] build docker image %s' % tag,
                  ['docker', 'build', '-f', os.path.join('docker', 'Dockerfile.Master'), '-t', tag,
                   '.'])
    logging.info('')
    return ret


def update_k8s_deployer():
    """
    Deprecated
    :return:
    """
    cfgpath = os.path.join(sys.path[0], 'deploy', 'node-monitor.yaml')
    logging.info('replace DOCKER_IMAGE_TAG in %s', cfgpath)
    cfgs = []
    with open(cfgpath) as k8scfg:
        cfg = yaml.load_all(k8scfg)
        for c in cfg:
            if c['kind'] == 'Deployment':
                c['spec']['template']['spec']['containers'][0]['imagePullPolicy'] = 'Always' \
                    if VERSION.endswith('SNAPSHOT') else 'IfNotPresent'
            cfgs.append(c)
    with open(cfgpath, 'w') as k8scfg:
        yaml.dump_all(cfgs, k8scfg)
    return True


def push_img():
    # push master image
    tag = MASTER_DOCKER_IMG_TAG + ':' + VERSION
    logging.info('push image:%s', tag)
    ret = run_cmd('push docker image %s' % tag, ['docker', 'push', tag])
    logging.info('push image:%s - [%s]', tag, 'SUCC' if ret else 'FAIL')

    tag = REPORT_UI_DOCKER_IMG_TAG + ':' + VERSION
    logging.info('push image:%s', tag)
    ret = run_cmd('push docker image %s'% tag, ['docker', 'push', tag])
    logging.info('push image:%s - [%s]', tag, 'SUCC' if ret else 'FAIL')
    logging.info('')

    return ret


if __name__ == '__main__':
    if '--prod' in sys.argv or '--production' in sys.argv:
        VERSION = VERSION % datetime.now().strftime('%Y%m%d%H%M%S')
    else:
        VERSION = VERSION % 'SNAPSHOT'
    logging.basicConfig(level=logging.INFO)
    start = datetime.now()
    logging.info('start build node-monitor@%s...', VERSION)
    if 'ui' in sys.argv:
        res = build_ui()
    elif 'master' in sys.argv:
        res = build_master()
    elif 'push' in sys.argv:
        push_img()
    else:
        res = build_ui() and build_master() and push_img()
    logging.info('node-monitor@%s build %s, take %s seconds',
                 VERSION,
                 'succeed' if res else 'failed.',
                 (datetime.now() - start).seconds)

