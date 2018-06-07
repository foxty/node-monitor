<template>
  <div>
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
  </div>
</template>

<script>
    import {Ajax} from '../common'

    export default {
        data () {
            return {
                summary: null,
                worstNodes: null
            }
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
    }
</script>

<style>
</style>