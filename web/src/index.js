import './asserts/all.css'
import 'bootstrap/dist/css/bootstrap.min.css'

import $ from 'jquery';
import Vue from 'vue';
import VueRouter from 'vue-router';
import VueECharts from 'vue-echarts'
import moment from 'moment';

import Dashboard from './components/Dashboard'
import Nodes from './components/Nodes'
import Node from './components/Node'
import NodeStatus from './components/NodeStatus'
import NodeServices from './components/NodeServices'
import ServiceList from './components/ServiceList'
import ServiceStatus from './components/ServiceStatus'
import Alarms from './components/Alarms'
import Settings from './components/Settings'

Vue.use(VueRouter)
Vue.component('chart', VueECharts)

Vue.filter('howLongAgo', function(date) {
    var result = "还未";
    if(date) {
        var curTime = new Date().getTime();
        var gap = curTime - date;
        var minutes = parseInt(gap / (1000 * 60));
        if (minutes / (60 * 24) > 1) {
            result = parseInt(minutes / (60 * 24)) + "天前";
        } else if (minutes / 60 > 1) {
            result = parseInt(minutes / 60) + "小时前";
        } else if (minutes > 0) {
            result = minutes + "分钟前";
        } else {
            result = "刚刚";
        }
    }
    return result;
});
Vue.filter('datePrint', function(millis) {
    var date = new Date(millis);
    return (date.getYear() + 1900) + "-" + (date.getMonth() + 1) + "-" + date.getDate();
});
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

Vue.component('pager', {
    template: '<div class="pagination pagination-centered" style="clear:both;">\
		<ul><li :class="{disabled:pagination.page<=1}"><a @click="to(pagination.page-1)">上一页</a></li>\
		<li v-for="p in pages"><a href="javascript:void(0);" @click="to(p)">{{p}}</a></li>\
		<li :class="{disabled:pagination.page >= pagination.maxPage}"><a @click="to(pagination.page+1)">下一页</a></li>\
		</ul></div>',
    props: ['pagination'],
    data: function() {
        var page = this.pagination.page;
        var maxPage = this.pagination.maxPage
        var factor = parseInt(page / 10);
        var startPage = factor * 10 + 1;
        var endPage = Math.min(maxPage, factor * 10 + 10);
        var pages = [];
        for(var p = startPage; p <= endPage; p ++) {
            pages.push(p);
        }
        return {pages:pages}
    },
    methods: {
        to: function(page) {
            if (page >= 1 && page <= this.pagination.maxPage) {
                this.$emit("to", page);
            } else {
                console.warn("Invalid page " + page);
            }
        }
    }
});

// In-place Editor
Vue.component("v-ipe", {
    template: '{{content}}',
    props: ['content'],
    data: function() {
        return {}
    },
    methods: {
    }
});

// Window
Vue.component("v-window", {
    template: "<div v-if='on'>" +
    "<div style='position:absolute;top:0;left:0;background-color:#666;opacity:0.5;width:100%;height:100%;z-index:100;'></div>" +
    "<div style='position:absolute;padding:10px;border:1px solid #999;background-color:#fff;z-index:110;" +
    "-webkit-border-radius:4px;-moz-border-radius:4px;border-radius:4px;width:{{w}}px;min-width:320px;'>" +
    "<span style='float:right;'><a @click='closeIt'>X</a></span>" +
    "<h4 v-if='title' style='margin:0;border-bottom:1px solid #D2B48C;padding:0 0 5px 10px;'>{{title}}</h4>" +
    "<div style='padding:5px 5px 5px 10px;'><slot>NO CONTENT!</slot></div>" +
    "</div>" +
    "</div>",
    props: ["name", "on", "title", "w", "h"],
    data: function() {
        return {};
    },
    methods: {
        closeIt: function() {
            this.$emit("close");
            console.log("window " + this.name + " closed")
        }
    }
});

// Report toolbar
Vue.component("report-toolbar", {
    template: `
    <div>
        <label>{{title}}</label> 
        
        <div class="btn-group" role="group">
            <button class="btn btn-sm btn-default"
                @click="changeRange('last_hour')">Last Hour</button>
            <button class="btn btn-sm btn-default"
                @click="changeRange('last_day')">Last Day</button>
            <button class="btn btn-sm btn-default"
                @click="changeRange('last_week')">Last Week</button>
        </div>
        
        <span><input type="text" placeholder="Start Time" size="10" style="text-align: center" v-model="startAt"/></span>
         - 
        <span><input type="text" placeholder="End Time" size="10" style="text-align: center" v-model="endAt"/></span>
        
        <button class="btn btn-sm btn-success" @click="reload()">Reload</button>
    </div>
    `,
    props: ['title'],
    data: function() {
        return {
            fmt: 'YY/MM/DD HH:mm',
            startAt: moment().subtract(1, 'h'),
            endAt: moment(),
        };
    },
    created: function() {
        this.changeRange('last_hour')
    },
    watch: {
        startAt: function() {
        },
        endAt: function() {
        },

    },
    methods: {

        changeRange: function(range) {
            const start = moment()
            const end = moment()
            switch (range) {
                case 'last_hour':
                    start.subtract(1, 'h')
                    break;
                case 'last_day':
                    start.subtract(24, 'h')
                    break;
                case 'last_week':
                    start.subtract(7, 'd')
                    break;
            }
            this.startAt = start.format(this.fmt)
            this.endAt = end.format(this.fmt)
            this.$emit('changeRange', start, end)
            console.log('change range of ' + this.title + ' to ' + this.startAt + ':' + this.endAt )
        },

        reload: function() {
            const start = moment(this.startAt, this.fmt)
            const end = moment(this.endAt, this.fmt)
            this.$emit('changeRange', start, end)
            console.log("reload data of " + this.title + ' to ' + this.startAt + ':' + this.endAt)
        }
    }
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


$(document).ajaxStart(function() {
    console.log('ajax start...')
}).ajaxStop(function(){
    console.log('ajax stop.')
}).ajaxError(function (event, jqXHR, ajaxSettings, error){
    var ct = jqXHR.getResponseHeader("Content-Type");
    if(/application\/json/.test(ct)) {
        alert(jqXHR.responseText);
    } else {
        alert('Request error, please check console log.')
        console.error(jqXHR.responseText);
    }
}).ready(function() {
    const app = new Vue({router})
    app.$mount('#app')
})