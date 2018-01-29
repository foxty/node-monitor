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
function stackChart(title, array, category, graphMapping) {
    //TODO:need fix
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
                       <th>Host</th>
                       <th>Create Time</th>
                       <th>Latest CPU Util(%)</th>
                       <th>Latest Mem Util(%)</th>
                       <th>Latest Load(1m)</th>
                       <th>Latest CS</th>
                   </tr>
               </thead>
               <tbody>
                   <tr v-for="a in agents">
                       <td><router-link :to="{name: 'agentStatus', params: {aid:a.aid}}">{{a.aid}}:{{a.name}}</router-link></td>
                       <td>{{a.host}}</td>
                       <td>{{a.created_at}}</td>
                       <td>{{a.last_cpu_util}}</td>
                       <td>{{a.last_mem_util}}</td>
                       <td>{{a.last_sys_load1}}</td>
                       <td>{{a.last_sys_cs}}</td>
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
                <div class="panel-heading">System</div>
                <div class="panel-body row">
                    <chart :options="sysLoad" style="width:100%;height:300px"></chart>
                    <div class='col-md-6'><chart :options="sysUsers" style="width:100%;height:300px"></chart></div>
                    <div class='col-md-6'><chart :options="sysCs" style="width:100%;height:300px"></chart></div>
                </div>
            </div>

            <div class="panel panel-default">
                <div class="panel-heading">CPU</div>
                <div class="panel-body row">
                    <chart :options="sysCpu" style="width:100%;height:300px"></chart>
                </div>
            </div>

            <div class="panel panel-default">
                <div class="panel-heading">Memory</div>
                <div class="panel-body row">
                    <div class="col-md-6"><chart :options="sysMemory" style="width:100%;height:300px"></chart></div>
                    <div class="col-md-6"><chart :options="sysSwap" style="width:100%;height:300px"></chart></div>
                </div>
            </div>
		</div>`,

		data: function() {
		    return {
		        agent: null,
		        sysReports: null,
		        cpuReports: null,
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
		    sysReports: function(n, o) {
		        var category = []
		        var load1 = []
		        var load5 = []
		        var load15 = []
		        var users = []
		        var sysin = []
		        var syscs = []

		        n.forEach(function(r) {
		            category.push(r.collect_at.substr(0, 19))
                    load1.push(r.load1)
                    load5.push(r.load5)
                    load15.push(r.load15)
                    users.push(r.users)
                    sysin.push(r.sys_in)
                    syscs.push(r.sys_cs)

		        })
		        this.sysLoad = {
                        title: {text: 'Sys Load'},
                        tooltip: {
                            trigger: 'axis'
                        },
                        legend: {
                                data:['Load1','Load5','Load15']
                        },
                        xAxis: {
                            type: 'category',
                            data: category
                        },
                        yAxis: {
                            type: 'value'
                        },
                        series: [{
                            data: load1,
                            type: 'line',
                            name: 'Load1'
                        },{
                            data:load5,
                            type:'line',
                            name:'Load5'
                        }, {
                            data:load15,
                            type:'line',
                            name:'Load15'
                        }]
                    }
                this.sysUsers = {
                        title: {text: 'Sys Users'},
                        tooltip: {
                            trigger: 'axis'
                        },
                        xAxis: {
                            type: 'category',
                            data: category
                        },
                        yAxis: {
                            type: 'value'
                        },
                        series: [{
                            data: users,
                            type: 'line'
                        }]
                    }
                this.sysCs = {
                        title: {text: 'Sys IN&CS'},
                        tooltip: {
                            trigger: 'axis'
                        },
                        legend: {
                            data: ['IN', 'CS']
                        },
                        xAxis: {
                            type: 'category',
                            data: category
                        },
                        yAxis: {
                            type: 'value'
                        },
                        series: [{
                            data: sysin,
                            type: 'line',
                            name: 'IN'
                        },{
                            data: syscs,
                            type: 'line',
                            name: 'CS'
                        }]
                    }
		    },
		    cpuReports: function(n, o) {
		        var category = []
		        var us = []
		        var sy = []
		        var id = []
		        var wa = []
		        var st = []
		        n.forEach(function(r) {
                    category.push(r.collect_at.substr(0, 19))
                    us.push(r.us)
                    sy.push(r.sy)
                    id.push(r.id)
                    wa.push(r.wa)
                    st.push(r.st)
                })
                this.sysCpu = {
                        title: {text: 'CPU'},
                        tooltip: {
                            trigger: 'axis'
                        },
                        legend: {
                                data:['User','System','Idle', 'Wait', 'Stolen']
                        },
                        xAxis: {
                            type: 'category',
                            data: category,
                            boundaryGap : false
                        },
                        yAxis: {
                            type: 'value',
                            axisLabel: {
                                formatter: '{value} %'
                            }
                        },
                        series: [{
                            name: 'User',
                            type: 'line',
                            stack:'Total',
                            areaStyle: {normal: {}},
                            data: us
                        },{
                            name: 'System',
                            type: 'line',
                            stack:'Total',
                            areaStyle: {normal: {}},
                            data: sy
                        }, {
                            name: 'Idle',
                            type: 'line',
                            stack:'Total',
                            areaStyle: {normal: {}},
                            data: id
                        }, {
                            name: 'Wait',
                            type: 'line',
                            stack:'Total',
                            areaStyle: {normal: {}},
                            data: wa
                        }, {
                            name: 'Stolen',
                            type: 'line',
                            stack:'Total',
                            areaStyle: {normal: {}},
                            data: st
                        }]
                    }
		    },
		    memReports: function(n, o) {
		        var category = []
                var total = []
                var usedMem = []
                var freeMem = []
                var usedSwap = []
                var freeSwap = []
                n.forEach(function(r) {
                    category.push(r.collect_at.substr(0, 19))
                    total.push(r.total_mem)
                    usedMem.push(r.used_mem)
                    freeMem.push(r.free_mem)
                    usedSwap.push(r.used_swap)
                    freeSwap.push(r.free_swap)
                })
                this.sysMemory = {
                        title: {text: 'Memory'},
                        tooltip: {
                            trigger: 'axis'
                        },
                        legend: {
                                data:['Used','Free']
                        },
                        xAxis: {
                            type: 'category',
                            data: category,
                            boundaryGap : false
                        },
                        yAxis: {
                            type: 'value',
                            axisLabel: {
                                formatter: '{value}M'
                            }
                        },
                        series: [{
                            name: 'Used',
                            type: 'line',
                            stack:'Total',
                            areaStyle: {normal: {}},
                            data: usedMem
                        },{
                            name: 'Free',
                            type: 'line',
                            stack:'Total',
                            areaStyle: {normal: {}},
                            data: freeMem
                        }]
                    }
                this.sysSwap = {
                        title: {text: 'Swap'},
                        tooltip: {
                            trigger: 'axis'
                        },
                        legend: {
                                data:['Used','Free']
                        },
                        xAxis: {
                            type: 'category',
                            data: category,
                            boundaryGap : false
                        },
                        yAxis: {
                            type: 'value',
                            axisLabel: {
                                formatter: '{value}M'
                            }
                        },
                        series: [{
                            name: 'Used',
                            type: 'line',
                            stack:'Total',
                            areaStyle: {normal: {}},
                            data: usedSwap
                        },{
                            name: 'Free',
                            type: 'line',
                            stack:'Total',
                            areaStyle: {normal: {}},
                            data: freeSwap
                        }]
                    }
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
                Ajax.get(`/api/agents/${aid}/report/system`, function(reports) {
                    self.sysReports = reports
                })
            },
            loadCpuReports: function() {
                var self = this;
                var aid = self.aid;
                Ajax.get(`/api/agents/${aid}/report/cpu`, function(reports) {
                    self.cpuReports = reports
                })
            },
            loadMemReports: function() {
                var self = this;
                var aid = self.aid;
                Ajax.get(`/api/agents/${aid}/report/memory`, function(reports) {
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