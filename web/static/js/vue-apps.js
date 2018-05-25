/**Vue Apps**/
const Dashboard = {
    template: `<div>
        <div class="row" style="padding:15px;">
            <div class="col-md-3 alert alert-success" style="text-align:center">
                <h3>{{summary ? summary.agent_count : 'N/A'}} Nodes</h3></div>
            <div class="col-md-3 alert alert-danger" style="text-align:center">
                <h3>{{summary ? summary.alarm_count : 'N/A'}} Alarms</h3></div>
            <div class="col-md-3 alert alert-info" style="text-align:center">
                <h3>{{summary ? summary.service_count : 'N/A'}} Services</h3></div>
            <div class="col-md-3 alert alert-info" style="text-align:center">
                <h3>{{summary ? summary.sample_count : 'N/A'}} Samples</h3></div>
        </div>
        <div class="row">
            <div class="col-md-4">
                <div class="panel panel-default">
                    <div class="panel-heading">
                        Worst Nodes (Top 10)
                    </div>
                    <div class="panel-body row">
                        <table class='table'>
                            <thead>
                                <tr>
                                    <th>Name</th>
                                    <th>Load1</th>
                                    <th>CPU%</th>
                                    <th>Memory%</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr v-for="node in worstNodes" style="padding:5px 0px 5px 10px;">
                                <td><router-link :to="{name: 'nodeStatus', params: {aid:node.aid}}">{{node.name}}</router-link></td>
                                <td>{{node.last_sys_load1}}</td>
                                <td>{{node.last_cpu_util}}</td>
                                <td>{{node.last_mem_util}}</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="panel panel-default">
                    <div class="panel-heading">
                        Worst Services
                    </div>
                    <div class="panel-body row">

                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="panel panel-default">
                    <div class="panel-heading">
                        New Alarms
                    </div>
                    <div class="panel-body row">

                    </div>
                </div>
            </div>
        </div>
    </div>`,

    data: function() {
        return {
            summary: null,
            worstNodes: null
        };
    },

    created: function() {
        this.loadSummary();
        this.loadWorstNodes();
    },

    methods: {
        loadSummary: function() {
            var self = this;
            Ajax.get('/api/dashboard/summary', function(summary) {
                self.summary = summary;
            })
        },
        loadWorstNodes: function() {
            var self = this;
            Ajax.get('/api/agents/by_load1', function(agents) {
                self.worstNodes = agents;
            })
        }
    }
};

const Nodes = {

    template: `<div>
        <table class="table table-bordered" v-if="agents && agents.length > 0">
            <thead>
                <tr>
                    <th>Name</th>
                    <th>Host</th>
                    <th>CPU Util(%)</th>
                    <th>Mem Util(%)</th>
                    <th>Load(1m)</th>
                    <th>CS</th>
                    <th>Last Recv Time</th>
                </tr>
            </thead>
            <tbody>
                <tr v-for="a in agents">
                    <td><router-link :to="{name: 'node', params: {aid:a.aid}}">{{a.name}}</router-link></td>
                    <td>{{a.host}}</td>
                    <td>{{a.last_cpu_util}}</td>
                    <td>{{a.last_mem_util}}</td>
                    <td>{{a.last_sys_load1}}</td>
                    <td>{{a.last_sys_cs}}</td>
                    <td>{{a.last_msg_at}}</td>
                </tr>
            </tbody>
       </table>
       <div v-if="!agents || agents.length == 0" class="alert alert-warning">no agents</div>
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

const Node = {
    props: ['aid'],

    template: `<div>
        <div class="col-md-2">
            <ul class="nav nav-pills nav-stacked">
              <li role="presentation" :class="{'active': $route.name == 'nodeStatus'}">
                <router-link :to="{name: 'nodeStatus', params: {aid:aid}}">Status</router-link>
              </li>
              <li role="presentation" :class="{'active': $route.name == 'nodeServices' || $route.name.startsWith('service')}">
                <router-link :to="{name: 'nodeServices', params: {aid:aid}}">Services</router-link>
              </li>
            </ul>
        </div>
        <div class="col-md-10">
            <div class="alert alert-info">Node {{agent ? agent.name + '@' + agent.host : ''}}</div>
            <router-view></router-view>
        </div>
    </div>`,

    data: function() {
        return {
            agent: null
        }
    },

    created: function() {
        this.loadData();
        // set default tab
        if(this.$route.name == 'node') router.push({name: 'nodeStatus'})
    },

    methods: {
        loadData: function() {
            var self = this;
            var aid = self.aid;
            Ajax.get(`/api/agents/${aid}`, function(agent) {
                self.agent = agent
            })
        },

        showServiceStatus: function(serviceId) {
            this.curServiceId = serviceId
        }
    }
}

const NodeStatus = {
        props: ['aid'],

		template: `<div>
            <div class="panel panel-default">
                <div class="panel-heading">
                    <report-toolbar title="Node Status" v-on:changeRange="reportRange = $event" v-on:reload="loadReports()"></report-toolbar>
                </div>
                <div class="panel-body">
                
                    <div v-if="sysReports && sysReports.length > 0">
                        <chart :options="sysLoad" style="width:100%;height:300px"></chart>
                        <div class='col-md-6'><chart :options="sysUsers" style="width:100%;height:300px"></chart></div>
                        <div class='col-md-6'><chart :options="sysCs" style="width:100%;height:300px"></chart></div>
                    </div>
                    <div v-else class="no_data">No system load data.</div>
                    
                    <div v-if="cpuReports && cpuReports.length > 0" style="clear: both;">
                        <chart :options="cpuChart" style="width:100%;height:300px"></chart>
                    </div>
                    <div v-else class="no_data">No CPU data.</div>
                    
                    <div v-if="memReports && memReports.length > 0">
                        <div class="col-md-6"><chart :options="memoryChart" style="width:100%;height:300px"></chart></div>
                        <div class="col-md-6"><chart :options="swapChart" style="width:100%;height:300px"></chart></div>
                    </div>
                    <div v-else class="no_data">No memory data.</div>
                    
                    <div v-if="diskReports && diskReports.length > 0" style="clear: both;">
                        <chart :options="diskChart" style="width:100%;height:300px"></chart>
                    </div>
                    <div v-else class="no_data">No disk data.</div>
                </div>
            </div>
		</div>`,

		data: function() {
		    return {
		        reportRange: 'last_hour',

		        sysReports: null,
		        sysLoad: null,
                sysUsers: null,
                sysCs: null,

		        cpuReports: null,
		        cpuChart: null,

		        memReports: null,
		        memoryChart: null,
		        swapChart: null,

		        diskReports: null,
		        diskChart: null
		    }
		},

		watch: {
		    reportRange: function(n, o) {
                if(n != o) {
                    this.loadSysReports()
                    this.loadCpuReports()
                    this.loadMemReports()
                    this.loadDiskReports()
                }
		    },
		    sysReports: function(n, o) {
		        this.sysLoad = genChartOption("Sys Load", n, "collect_at",
		                            {"Load1":"load1", "Load5":"load5", "Load15":"load15"});
                this.sysUsers = genChartOption("Sys Users",n, "collect_at", {"Users":"users"});
                this.sysCs =  genChartOption("Sys IN&CS", n, "collect_at", {"IN":"sys_in", "CS":"sys_cs"});
		    },
		    cpuReports: function(n, o) {
                this.cpuChart = genChartOption("CPU", n, "collect_at",
                                {"User":"us","System":"sy","Idle":"id","Wait":"wa","Stolen":"st"},
                                {isStack:true, yAxisFmt: "{value}%"});
		    },
		    memReports: function(n, o) {
                this.memoryChart = genChartOption("Memory", n, "collect_at",
                                    {"Used":"used_mem", "Free":"free_mem"},
                                    {isStack:true, yAxisFmt:"{value}M"});
                this.swapChart = genChartOption("Swap", n, "collect_at",
                                   {"Used":"used_swap", "Free":"free_swap"},
                                   {isStack:true, yAxisFmt:"{value}M"});
		    },
		    diskReports: function(n, o) {
		        var reportsMap = {}
		        var spMapping = {}
		        n.forEach(x => {
                    if(!reportsMap[x.collect_at]) {
                        reportsMap[x.collect_at] = {'aid': x.aid, collect_at: x.collect_at}
                    }
		            reportsMap[x.collect_at][x.mount_point] = Math.round(x.used*100.0/x.size)
		            if(!spMapping[x.mount_point]) {
		                spMapping[x.mount_point] = x.mount_point
		            }
		        })
                var reports = []
                var i=0
                for(t in reportsMap) {
                    reports[i++] = reportsMap[t]
                }
		        this.diskChart = genChartOption("Disk Util", reports, "collect_at",
                                               spMapping,
                                               {yAxisFmt:"{value}%"});
		    }
		},

		created: function() {
            this.loadReports()
		},

		methods: {

            loadReports: function() {
                this.loadSysReports();
                this.loadCpuReports();
                this.loadMemReports();
                this.loadDiskReports();
            },

            loadSysReports: function() {
                var self = this;
                var aid = self.aid;
                var range = self.reportRange
                Ajax.get(`/api/agents/${aid}/report/system/${range}`, function(reports) {
                    self.sysReports = reports
                })
            },
            loadCpuReports: function() {
                var self = this;
                var aid = self.aid;
                var range = self.reportRange
                Ajax.get(`/api/agents/${aid}/report/cpu/${range}`, function(reports) {
                    self.cpuReports = reports
                })
            },
            loadMemReports: function() {
                var self = this;
                var aid = self.aid;
                var range = self.reportRange
                Ajax.get(`/api/agents/${aid}/report/memory/${range}`, function(reports) {
                    self.memReports = reports
                })
            },
            loadDiskReports: function() {
                var self = this;
                var aid = self.aid;
                var range = self.reportRange
                Ajax.get(`/api/agents/${aid}/report/disk/${range}`, function(reports) {
                    self.diskReports = reports
                })
            }
		}
	}

const NodeServices = {
    props: ['aid'],

    template: `
    <div>
        <ul class="nav nav-tabs">
            <li role="presentation" :class="{'active': $route.name == 'serviceList'}">
                <router-link :to="{name: 'serviceList', params: {aid: aid}}">
                    List
                </router-link>
            </li>
            <li role="presentation" :class="{'active': $route.params.service_id == s.id}" v-for="s in services" >
                <router-link :to="{name: 'serviceStatus', params: {aid:s.aid, service_id:s.id}}">{{s.name}}</router-link>
            </li>
        </ul>
        <div style="margin-top: 10px">
            <router-view :key="curServiceId" 
                v-bind:services="services" 
                v-bind:services_status_map="services_status_map">
            </router-view>
        </div>
    </div>`,

    data: function() {
        return {
            services: null,
            services_status_map: {},
            curServiceId: null
        }
    },

    created: function() {
        var self = this;
        self.loadServices();
        router.push({name: 'serviceList'})
        router.afterEach((to, from) => {
            self.curServiceId = to.params.service_id
        })
    },

    methods: {
        loadServices: function() {
            var self = this;
            var aid = self.aid
            Ajax.get(`/api/agents/${aid}/services`, function(data) {
                self.services = data.services;
                self.services_status_map = data.services_status_map;
                console.debug('get services by aid ' + aid)
                console.debug(data)
            })
        }
    }
}

const ServiceList = {
    props: ['aid', 'services', 'services_status_map'],

    template: `
    <div>
        <table class="table table-bordered" v-if="services && services.length > 0">
            <thead>
                <tr>
                    <th>Name</th>
                    <th>Type</th>
                    <th>Status</th>
                    <th>PID</th>
                    <th>CPU Util(%)</th>
                    <th>Mem Util(%)</th>
                    <th>Last Report Time</th>
                </tr>
            </thead>
            <tbody>
                <tr v-for="s in services">
                    <td><router-link :to="{name: 'serviceStatus', params: {aid:aid, service_id:s.id}}">{{s.name}}</router-link></td>
                    <td>{{s.type}}</td>
                    <td>
                        <span class="label" :class="{'label-success': s.status=='active', 'label-default': s.status=='inactive'}">{{s.status}}</span>
                    </td>
                    <td>{{s.pid}}</td>
                    <td>{{services_status_map[s.id] ? services_status_map[s.id].cpu_util : '-'}}</td>
                    <td>{{services_status_map[s.id] ? services_status_map[s.id].mem_util : '-'}}</td>
                    <td>{{s.last_report_at}}</td>
                </tr>
            </tbody>
        </table>
        <div v-if="!services || services.length == 0" class="alert alert-warning">no service discovered.</div>
    </div>`,

    data: function() {
        return {}
    },

    created: function() {
    },

    methods: {
    }
}

const ServiceStatus = {
    props: ['aid', 'service_id'],

    template: `
    <div>
        <div class="panel panel-default">
            <div class="panel-heading">
                <report-toolbar title="Service Status" v-on:changeRange="reportRange = $event" v-on:reload="loadReports()"></report-toolbar>
            </div>
            <div class="panel-body row">
                <div v-if="pidstatReports && pidstatReports.length > 0">
                    <div><chart :options="cpuChart" style="width:100%;height:300px"></chart></div>
                    <div><chart :options="memoryChart" style="width:100%;height:300px"></chart></div>
                </div>
                <div v-else class="no_data">No pidstat data.</div>
                
                <div v-if="jstatgcReports && jstatgcReports.length > 0">
                    <div style="padding: 15px;">
                        <label>GC Stats</label> 
                        <table class="table table-bordered">
                            <thead>
                                <tr>
                                    <th>Category</th>
                                    <th>Start</th>
                                    <th>End</th>
                                    <th>YGC</th>
                                    <th>YGC Time(s)</th>
                                    <th>AVG Time(s)</th>
                                    <th>FGC</th>
                                    <th>FGC Time(s)</th>
                                    <th>AVG Time(s)</th>
                                    <th>Throughput</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr v-for="stat in jstatgcStats">
                                    <td>{{stat.category}}</td>
                                    <td>{{stat.start_at}}</td>
                                    <td>{{stat.end_at}}</td>
                                    <td>{{stat.ygc}}</td>
                                    <td>{{stat.ygct}}</td>
                                    <td>{{stat.avg_ygct | decimal}}</td>
                                    <td>{{stat.fgc}}</td>
                                    <td>{{stat.fgct}}</td>
                                    <td>{{stat.avg_fgct | decimal}}</td>
                                    <td>{{stat.throughput | decimal(6) | percent}}</td>
                                </tr>
                            </tbody>
                        </table>   
                    </div>
                    <div><chart :options="jmemoryChart" style="width:100%;height:300px"></chart></div>
                </div>
                <div v-else class="no_data">No jstat-gc data.</div>
            </div>
        </div>
    </div>`,

    data: function() {
        return {
            reportRange: 'last_hour',
            service: null,
            serviceHistory:null,

            pidstatReports: null,
            cpuChart: null,
            memoryChart: null,

            jstatgcReports: null,
            jstatgcStats: null,
            gcStatusAll: null,
            gcStatusDelta: null,
            jmemoryChart:null,
            jgcChart:null
        }
    },

    created: function() {
        this.loadReports()
    },

    watch: {
        reportRange: function(o, n) {
            this.loadReports();
        },

        pidstatReports: function(n, o) {
            this.cpuChart = genChartOption("CPU Utilization", n, "collect_at",
                                           {"Total":"cpu_util", "SYS":"cpu_sy", "USER":"cpu_us"},
                                           {isStack:true, yAxisFmt:"{value}%"});
            this.memoryChart = genChartOption("Memory Utilization", n, "collect_at",
                                {"Util":"mem_util"},
                                {isStack:true, yAxisFmt:"{value}%"});

        },

        jstatgcReports: function(n, o) {
            if(!n || n.length == 0) {
                console.warn('No data for jstat-gc')
                return;
            }
            this.jgcChart = genChartOption("CPU Utilization", n, "collect_at",
                {"Total":"cpu_util", "SYS":"cpu_sy", "USER":"cpu_us"},
                {isStack:false, yAxisFmt:"{value}%"});
            this.jmemoryChart = genChartOption("Java Heap Util", n, "collect_at",
                {"S0U":"s0u", "S1U":"s1u", "EU":"eu", "OU":"ou"},
                {isStack:true, yAxisFmt: function (v, index) {
                        return Math.round(v/1024) + 'MB'
                    }
                });

        }
    },

    methods: {
        loadReports: function() {
            this.loadServiceInfo()
            this.loadPidstatReports()
            this.loadJstatgcReports()
        },

        loadServiceInfo: function() {
            var self = this;
            var aid = self.aid;
            var sid = self.service_id
            var range = self.reportRange
            Ajax.get(`/api/agents/${aid}/services/${sid}/${range}`, function(resp) {
                self.service = resp.service
                self.service_history = resp.service_history
            })
        },

        loadPidstatReports: function() {
            var self = this;
            var aid = self.aid;
            var sid = self.service_id
            var range = self.reportRange
            Ajax.get(`/api/agents/${aid}/services/${sid}/report/pidstat/${range}`, function(reports) {
                self.pidstatReports = reports
            })
        },

        loadJstatgcReports: function() {
            var self = this;
            var aid = self.aid;
            var sid = self.service_id
            var range = self.reportRange
            Ajax.get(`/api/agents/${aid}/services/${sid}/report/jstatgc/${range}`, function(resp) {
                self.jstatgcReports = resp.reports
                self.jstatgcStats = resp.gcstats
            })
        }
    }
}

const Alarms = {
		template: `<div>
		    Alarms
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
		    Settings
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
    })