<template>
    <div>
        <div class="panel panel-default">
            <div class="panel-heading">
                <report-toolbar title="Service Status" v-on:changeRange="changeRange" v-on:reload="loadReports()"></report-toolbar>
            </div>
            <div class="panel-body row">
                <div v-if="pidstatReports && Object.keys(pidstatReports).length > 0">
                    <div><chart :options="cpuChart" style="width:100%;height:300px"></chart></div>
                    <div><chart :options="memoryChart" style="width:100%;height:300px"></chart></div>
                    <div><chart :options="rssChart" style="width:100%;height:300px"></chart></div>
                    <div><chart :options="vszChart" style="width:100%;height:300px"></chart></div>
                </div>
                <div v-else class="no_data">No pidstat data.</div>

                <div v-if="jstatgcReports && Object.keys(jstatgcReports).length > 0">
                    <!--div style="padding: 15px;">
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
                                <td>{{stat.ygct | decimal}}</td>
                                <td>{{stat.avg_ygct | decimal}}</td>
                                <td>{{stat.fgc}}</td>
                                <td>{{stat.fgct | decimal}}</td>
                                <td>{{stat.avg_fgct | decimal}}</td>
                                <td>{{stat.throughput | decimal(6) | percent}}</td>
                            </tr>
                            </tbody>
                        </table>
                    </div-->
                    <div><chart :options="jmemoryChart" style="width:100%;height:300px"></chart></div>
                </div>
                <div v-else class="no_data">No jstat-gc data.</div>
            </div>
        </div>
    </div>
</template>

<script>
    import {genChartOption} from '../common'

    export default {
        props: ['aid', 'service_id'],

        data: function() {
            return {
                startAt: null,
                endAt: null,

                service: null,
                serviceHistory:null,

                pidstatReports: null,
                cpuChart: null,
                memoryChart: null,
                rssChart: null,
                vszChart: null,

                jstatgcReports: null,
                jstatgcStats: null,
                jmemoryChart:null,
                jgcChart:null
            }
        },

        created: function() {},

        methods: {
            changeRange: function(startAt, endAt) {
                this.startAt = startAt
                this.endAt = endAt
                this.loadReports()
            },

            loadReports: function() {
                var self = this;
                var aid = self.aid;
                var sid = self.service_id
                var startAt = self.startAt.valueOf()
                var endAt = self.endAt.valueOf()
                var q = `start_at=${startAt}&end_at=${endAt}`
                var markerLines = []
                new Promise(function(resolve){
                    // Load service history at begin
                    self.$http.get(`/api/agents/${aid}/services/${sid}?${q}`).then(resp => {
                        return resp.json()
                    }).then(data => {
                        self.service = data.service
                        self.service_history = data.service_history
                        markerLines = self.genRestartMarkerConfig(self.service_history)
                        resolve()
                    })
                }).then(function(){
                    self.$http.get(`/api/agents/${aid}/services/${sid}/report/pidstat?${q}`).then(resp => {
                        return resp.json()
                    }).then(reports => {
                        self.pidstatReports = reports
                        self.genPidstatReports(reports, markerLines)
                    })
                    self.$http.get(`/api/agents/${aid}/services/${sid}/report/jstatgc?${q}`).then(resp => {
                        return resp.json()
                    }).then(resp => {
                        self.jstatgcReports = resp.reports
                        self.jstatgcStats = resp.gcstats
                        self.genJstatgcReports(resp.reports, markerLines)
                    })
                })

            },

            genRestartMarkerConfig: function(serviceHistory) {
                var markers = []
                serviceHistory.forEach(function(sh) {
                    markers.push({xAxis: sh.collect_at || sh.recv_at})
                })
                return {
                    label: {formatter: 'R'},
                    lineStyle: {type: 'solid'},
                    data:markers
                }
            },

            genPidstatReports: function(n, markerLine) {
                this.cpuChart = genChartOption("CPU Utilization", n,
                    {"CPU":"service.pidstat.cpu_util"},
                    {yAxisFmt:"{value}%", yAxisMax:100, markLine: markerLine})
                this.memoryChart = genChartOption("Memory Utilization", n,
                    {"Util":"service.pidstat.mem_util"},
                    {stack:true, yAxisFmt:"{value}%", yAxisMax:100, markLine: markerLine})
                this.rssChart = genChartOption("RSS", n,
                    {"RSS":"service.pidstat.mem_rss"},
                    {yAxisFmt:"{value}K", markLine: markerLine})
                this.vszChart = genChartOption("VSZ", n,
                    {"VSZ":"service.pidstat.mem_vsz"},
                    {yAxisFmt:"{value}K", markLine: markerLine})

            },

            genJstatgcReports: function(n, markerLine) {
                if(!n || Object.keys(n).length == 0) {
                    console.warn('No data for jstat-gc')
                    return;
                }
                this.jmemoryChart = genChartOption("Java Heap Util", n,
                    {"S0U":"service.jstatgc.s0u", "S1U":"service.jstatgc.s1u",
                        "EU":"service.jstatgc.eu", "OU":"service.jstatgc.ou"},
                    {stack:true, yAxisFmt: function (v, index) {
                            return Math.round(v/1024) + 'MB'
                        }
                        , markLine: markerLine});

            }
        }
    }
</script>

<style>
</style>