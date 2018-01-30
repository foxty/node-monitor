/**jQuery Defaults**/
$(document).ajaxStart(function() {
	console.log('ajax start...')
}).ajaxStop(function(){
	console.log('ajax stop.')
}).ajaxError(function (event, jqXHR, ajaxSettings, error){
	var ct = jqXHR.getResponseHeader("Content-Type");
	if(/application\/json/.test(ct)) {
		alert(jqXHR.responseText);
	} else {
		console.error(jqXHR.responseText);
	}
})

/** Shortcut for ajax **/
var Ajax = {
	
	doAjax: function(url, method, data, succ) {
		if(typeof(data) == 'function' && succ == undefined) {
			succ = data;
		}
		$.ajax({
		    url: url,
		    type: method,
		    data: data,
		    dataType: "json",
		    success: succ
		});
	},

	get: function(url, succ) {
	    this.doAjax(url,'GET', succ);
	},

	post: function(url, data, succ) {
		this.doAjax(url, "POST", data, succ);
	},
	
	put: function(url, data, succ) {
		this.doAjax(url, "PUT", data, succ);
	},
	
	delete: function(url, succ) {
		this.doAjax(url, "DELETE", null, succ);
	}
}

/**Filters**/
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


/**Components**/
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

/**Echarts**/
function genChartOption(title, data, cateProp, seriesPropsMapping, graphOptions) {
    graphOptions = graphOptions || {}
    graphOptions.isStack = graphOptions.isStack || false
    graphOptions.yAxisFmt = graphOptions.yAxisFmt || '{value}'
    var category = []
    var seriesMap = {}
    var legends = []
    data.forEach(function(d) {
        category.push(d[cateProp]);
        for(serieName in seriesPropsMapping) {
            if (!seriesMap[serieName]) {
                seriesMap[serieName] = {name: serieName, type: 'line', data: []};
            }
            serie = seriesMap[serieName];
            serieDataProp = seriesPropsMapping[serieName];
            if(graphOptions.isStack) {
                serie.stack = 'Total';
                serie.areaStyle = {normal: {}};
            }
            serie.data.push(d[serieDataProp])
        }
    })
    var series = [];
    for(serieName in seriesMap) {
        legends.push(serieName);
        series.push(seriesMap[serieName]);
    }

    return {
        title: {text: title},
        tooltip: {
            trigger: 'axis'
        },
        legend: {
                data:legends
        },
        xAxis: {
            type: 'category',
            data: category,
            boundaryGap : false,
            axisLabel: {
                formatter: function(v, idx) {
                    return v && v.length > 19 ?  v.substr(0,19) : v;
                }
            }
        },
        yAxis: {
            type: 'value',
            axisLabel: {
                formatter: graphOptions.yAxisFmt
            }
        },
        dataZoom: [{
                type: 'slider', // 这个 dataZoom 组件是 slider 型 dataZoom 组件
                start: 0,      // 左边在 10% 的位置。
                end: 100         // 右边在 60% 的位置。
            }
        ],
        series: series
    }
}

/**Vue Apps**/
const Dashboard = {
		template: `<div><div class="page-header"><h1>Dashboard</h1></div>
		</div>`,
		data: function() {
		    return {};
		},

		methods: {
            hello: function() {
                alert('hello')
            }
		}
	};

const Agents = {
		template: `<div><div class="page-header"><h1>Agent List</h1></div>
		    <table class="table" v-if="agents">
		        <thead>
                    <tr>
                        <th>Name</th>
                        <th>Node Host</th>
                        <th>Service(s)</th>
                        <th>CPU Util(%)</th>
                        <th>Mem Util(%)</th>
                        <th>Load(1m)</th>
                        <th>CS</th>
                        <th>Reports</th>
                        <th>Create Time</th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="a in agents">
                        <td>{{a.name}}</td>
                        <td>{{a.host}}</td>
                        <td>N/A</td>
                        <td>{{a.last_cpu_util}}</td>
                        <td>{{a.last_mem_util}}</td>
                        <td>{{a.last_sys_load1}}</td>
                        <td>{{a.last_sys_cs}}</td>
                        <td>
                            <router-link :to="{name: 'agentStatus', params: {aid:a.aid}}">
                                Reports <span class="glyphicon glyphicon-stats" aria-hidden="true"></span>
                            </router-link>
                        </td>
                        <td>{{a.created_at}}</td>
                    </tr>
                </tbody>
           </table>
           <div v-if="!agents" class="well">no agents</div>
       </div>`,
		data: function() {
		    return {
		        title:'Agent List',
		        agents: null
		    }
		},

		created: function() {
		    this.loadAgents()
		},

		methods: {
            loadAgents: function() {
                var self = this;
                Ajax.get('/api/agents', function(data) {
                    self.agents = data;
                })
            }
		}
	}

const AgentStatus = {
        props: ['aid'],

		template: `<div><div class="page-header"><h1>Agent {{aid}} Status</h1></div>
            <div class="panel panel-default">
                <div class="panel-heading">
                    System
                    <button class="btn btn-sm btn-link" @click="sysReportsRange='last_hour'">Last Hour</button>
                    <button class="btn btn-sm btn-link" @click="sysReportsRange='last_day'">Last Day</button>
                    <button class="btn btn-sm btn-link" @click="sysReportsRange='last_week'">Last Week</button>
                    <button class="btn btn-sm btn-success" @click="loadSysReports()">Reload</button>
                </div>
                <div class="panel-body row">
                    <chart :options="sysLoad" style="width:100%;height:300px"></chart>
                    <div class='col-md-6'><chart :options="sysUsers" style="width:100%;height:300px"></chart></div>
                    <div class='col-md-6'><chart :options="sysCs" style="width:100%;height:300px"></chart></div>
                </div>
            </div>

            <div class="panel panel-default">
                <div class="panel-heading">
                    CPU
                    <button class="btn btn-sm btn-link" @click="cpuReportsRange='last_hour'">Last Hour</button>
                    <button class="btn btn-sm btn-link" @click="cpuReportsRange='last_day'">Last Day</button>
                    <button class="btn btn-sm btn-link" @click="cpuReportsRange='last_week'">Last Week</button>
                    <button class="btn btn-sm btn-success" @click="loadCpuReports()">Reload</button>
                 </div>
                <div class="panel-body row">
                    <chart :options="sysCpu" style="width:100%;height:300px"></chart>
                </div>
            </div>

            <div class="panel panel-default">
                <div class="panel-heading">
                    Memory
                    <button class="btn btn-sm btn-link" @click="memReportsRange='last_hour'">Last Hour</button>
                    <button class="btn btn-sm btn-link" @click="memReportsRange='last_day'">Last Day</button>
                    <button class="btn btn-sm btn-link" @click="memReportsRange='last_week'">Last Week</button>
                    <button class="btn btn-sm btn-success" @click="loadMemReports()">Reload</button>
                </div>
                <div class="panel-body row">
                    <div class="col-md-6"><chart :options="sysMemory" style="width:100%;height:300px"></chart></div>
                    <div class="col-md-6"><chart :options="sysSwap" style="width:100%;height:300px"></chart></div>
                </div>
            </div>
		</div>`,

		data: function() {
		    return {
		        agent: null,
		        sysReportsRange: 'last_hour',
		        sysReports: null,
		        cpuReportsRange: 'last_hour',
		        cpuReports: null,
		        memReportsRange: 'last_hour',
		        memReports: null,
		        sysLoad: null,
		        sysUsers: null,
		        sysCs: null,
		        sysCpu: null,
		        sysMemory: null,
		        sysSwap: null
		    }
		},

		watch: {
		    sysReportsRange: function(n, o) {
                if(n != o) {
                    this.loadSysReports()
                }
		    },
		    cpuReportsRange: function(n, o) {
		        if (n != 0) {
		            this.loadCpuReports()
		        }
		    },
		    memReportsRange: function(n, o) {
		        if(n != o) {
		            this.loadMemReports()
		        }
		    },
		    sysReports: function(n, o) {
		        this.sysLoad = genChartOption("Sys Load", n, "collect_at",
		                            {"Load1":"load1", "Load5":"load5", "Load15":"load15"});
                this.sysUsers = genChartOption("Sys Users",n, "collect_at", {"Users":"users"});
                this.sysCs =  genChartOption("Sys IN&CS", n, "collect_at", {"IN":"sys_in", "CS":"sys_cs"});
		    },
		    cpuReports: function(n, o) {
                this.sysCpu = genChartOption("CPU", n, "collect_at",
                                {"User":"us","System":"sy","Idle":"id","Wait":"wa","Stolen":"st"},
                                {isStack:true, yAxisFmt: "{value}%"});
		    },
		    memReports: function(n, o) {
                this.sysMemory = genChartOption("Memory", n, "collect_at",
                                    {"Used":"used_mem", "Free":"free_mem"},
                                    {isStack:true, yAxisFmt:"{value}M"});
                this.sysSwap = genChartOption("Swap", n, "collect_at",
                                   {"Used":"used_swap", "Free":"free_swap"},
                                   {isStack:true, yAxisFmt:"{value}M"});
		    }
		},

		created: function() {
            this.loadSysReports();
            this.loadCpuReports();
            this.loadMemReports();
		},

		methods: {
            loadSysReports: function() {
                var self = this;
                var aid = self.aid;
                var range = self.sysReportsRange
                Ajax.get(`/api/agents/${aid}/report/system/${range}`, function(reports) {
                    self.sysReports = reports
                })
            },
            loadCpuReports: function() {
                var self = this;
                var aid = self.aid;
                var range = self.cpuReportsRange
                Ajax.get(`/api/agents/${aid}/report/cpu/${range}`, function(reports) {
                    self.cpuReports = reports
                })
            },
            loadMemReports: function() {
                var self = this;
                var aid = self.aid;
                var range = self.memReportsRange
                Ajax.get(`/api/agents/${aid}/report/memory/${range}`, function(reports) {
                    self.memReports = reports
                })
            }
		}
	}

const AgentServices = {
    template: `Agent Services`
}

const Alarms = {
		template: `<div>
		<div class="page-header"><h1>Alarms</h1></div>
		</div>`,
		data: function() {
		    return {}
		},

		created: function() {
		},

		methods: {

		}
	}


const Settings = {
		template: `<div>
		    <div class="page-header"><h1>Settings</h1></div>
		</div>`,
		data: function() {
		    return {}
		},

		created: function() {
		},

		methods: {

		}
	}

const router = new VueRouter({
      routes: [
        // 动态路径参数 以冒号开头
        {path: '/dashboard', component:  Dashboard},
        {path: '/agents', component:  Agents},
        {path: '/agents/:aid/status', name: 'agentStatus', component: AgentStatus, props: true},
        {path: '/agents/:aid/services', name: 'agentServices', component: AgentServices, props: true},
        {path: '/alarms', component:  Alarms},
        {path: '/settings', component:  Settings}
      ]
    })