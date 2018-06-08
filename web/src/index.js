import './asserts/all.css'
import 'bootstrap/dist/css/bootstrap.min.css'

import Vue from 'vue'
import VueRouter from 'vue-router'
import VueResource from 'vue-resource'
import VModal from 'vue-js-modal'
import moment from 'moment'

import Dashboard from './components/Dashboard'
import Nodes from './components/Nodes'
import Node from './components/Node'
import NodeStatus from './components/NodeStatus'
import NodeServices from './components/NodeServices'
import ServiceList from './components/ServiceList'
import ServiceStatus from './components/ServiceStatus'
import Alarms from './components/Alarms'
import Settings from './components/Settings'
import ReportToolbar from './components/ReportToolbar'

Vue.use(VueRouter)
Vue.use(VueResource)
Vue.http.headers.common['Content-Type'] = 'application/json';
Vue.http.interceptors.push(function(request) {
    console.log('start ajax..')
    // return response callback
    return function(response) {
        if(response.status == 0) {
            this.$modal.show('dialog', {
                title: 'Connection Error',
                text: 'Seems you lost the connection with server, please check your network or contact our admin.',
            })
        } else if (response.status >= 300) {
            response.text().then(data => {
                this.$modal.show('dialog', {
                    title: 'Error',
                    text: data,
                })
                console.error('error of ajax code=' + response.status + ', body=' + data)
            })
        }
        console.log('end ajax')
    };
});
Vue.use(VModal, { dialog: true, dynamic: true })

Vue.component('chart', () => import('vue-echarts'))
Vue.component("report-toolbar", ReportToolbar);
Vue.filter('percent', function(number) {
    return (number * 100) + '%'
});
Vue.filter('decimal', function(number, precision) {
    if (precision == undefined) {
        precision = 2
    }
    var pows = Math.pow(10, precision)
    var d = Math.round(number * pows) / pows
    return d;
});

moment.locale('cn', {
    relativeTime : {
        future: "in %s",
        past:   "%s之前",
        s:  "几秒",
        m:  "一分钟",
        mm: "%d分钟",
        h:  "一小时",
        hh: "%d小时",
        d:  "一天",
        dd: "%d天",
        M:  "一个月",
        MM: "%d个月",
        y:  "一年",
        yy: "%d年"
    }
});

const router = new VueRouter({
    routes: [
        // 动态路径参数 以冒号开头
        {path: '/', redirect: {name: 'dashboard'}},
        {path: '/dashboard', name: 'dashboard', component: Dashboard},
        {path: '/nodes', component: Nodes},
        {path: '/nodes/:aid', name:'node', component: Node, props:true, children: [
                {path: 'status', name: 'nodeStatus', component: NodeStatus, props: true},
                {path: 'services', name: 'nodeServices', component: NodeServices, props: true, children: [
                        {path: 'list', name: 'serviceList', component: ServiceList, props: true},
                        {path: ':service_id/status', name: 'serviceStatus', component: ServiceStatus, props: true}
                    ]},
            ]
        },
        {path: '/alarms', component:  Alarms},
        {path: '/settings', component:  Settings}
    ]
});

const app = new Vue({router})
app.$mount('#app')