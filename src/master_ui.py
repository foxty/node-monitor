#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Created on 2017-12-22
@author: foxty

UI for master node
"""
import logging
from flask import Flask, render_template
logging.basicConfig(level=logging.INFO)
app = Flask(__name__,
            static_folder='../web/static/',
            static_url_path='/static',
            template_folder='../web/template/')


@app.route("/")
def index():
    return render_template('index.html')


def ui_main(host='0.0.0.0', port=8080, debug=False):
    logging.info('starting master ui...')
    app.jinja_env.variable_start_string = '{-'
    app.jinja_env.variable_end_string = '-}'
    app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    ui_main(port=8081, debug=True)