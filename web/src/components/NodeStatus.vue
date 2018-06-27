<template>
    <div>
        <div class="panel panel-default">
            <div class="panel-heading">
                <report-toolbar title="Node Status" v-on:changeRange="changeRange" v-on:reload="loadReports()"></report-toolbar>
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
    </div>
</template>

<script>
    import {genChartOption} from '../common'

    export default {
        props: ['aid'],

        data: function() {
            return {
                startAt: null,
                endAt: null,

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
                    this.loadReports()
                }
            },
            sysReports: function(n, o) {
                this.sysLoad = genChartOption("Sys Load", n, "collect_at",
                    {"Load1":"load1", "Load5":"load5", "Load15":"load15"},
                    {yAxisMax:function(value) { return value.max < 10 ? 10 : value.max + 5 }});
                this.sysUsers = genChartOption("Sys Users",n, "collect_at", {"Users":"users"},
                    {yAxisMax:function(value) { return value.max < 10 ? 10 : value.max + 5 }});
                this.sysCs =  genChartOption("Sys IN&CS", n, "collect_at", {"IN":"sys_in", "CS":"sys_cs"});
            },
            cpuReports: function(n, o) {
                this.cpuChart = genChartOption("CPU", n, "collect_at",
                    {"User":"us","System":"sy", "Wait":"wa","Stolen":"st"},
                    {stack:true, yAxisFmt: "{value}%", yAxisMax:100,});
            },
            memReports: function(n, o) {
                this.memoryChart = genChartOption("Memory", n, "collect_at",
                    {"Used":"used_mem", "Free":"free_mem"},
                    {stack:true, yAxisFmt:"{value}M"});
                this.swapChart = genChartOption("Swap", n, "collect_at",
                    {"Used":"used_swap", "Free":"free_swap"},
                    {stack:true, yAxisFmt:"{value}M"});
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
                for(var t in reportsMap) {
                    reports[i++] = reportsMap[t]
                }
                this.diskChart = genChartOption("Disk Util", reports, "collect_at",
                    spMapping,
                    {yAxisFmt:"{value}%", yAxisMax:100,});
            }
        },

        created: function() {
            //this.loadReports()
        },

        methods: {
            changeRange: function(startAt, endAt) {
                this.startAt = startAt
                this.endAt = endAt
                this.loadReports()
            },

            loadReports: function() {
                var self = this;
                var aid = self.aid;
                var startAt = self.startAt.valueOf()
                var endAt = self.endAt.valueOf()
                var q = `start_at=${startAt}&end_at=${endAt}`
                self.$http.get(`/api/agents/${aid}/report/system?${q}`).then(resp => {
                    return resp.json()
                }).then(reports => {
                    self.sysReports = reports
                    console.log(reports)
                })

                self.$http.get(`/api/agents/${aid}/report/cpu?${q}`).then(resp => {
                    return resp.json()
                }).then(reports => {
                    self.cpuReports = reports
                })

                self.$http.get(`/api/agents/${aid}/report/memory?${q}`).then(resp => {
                    return resp.json()
                }).then(reports => {
                    self.memReports = reports
                })

                self.$http.get(`/api/agents/${aid}/report/disk?${q}`).then(resp => {
                    return resp.json()
                }).then(reports => {
                    self.diskReports = reports
                })
            },
        }
    }
</script>

<style>
</style>