<template>
    <div>
        <div style="margin-bottom: 5px;">
            <button type="button" class="btn btn-success" @click="addNode">
                <span class="glyphicon glyphicon-plus"></span>
                Add Node
            </button>
            <button type="button" class="btn btn-default" @click="loadAgents">
                <span class="glyphicon glyphicon-refresh"></span>
                Reload
            </button>
            <span> Total {{agents ? agents.length : ''}} Nodes</span>
        </div>
        <table class="table table-bordered" v-if="agents && agents.length > 0">
            <thead>
            <tr>
                <th>Name</th>
                <th>Status</th>
                <th>Host</th>
                <th>CPU Util(%)</th>
                <th>Mem Util(%)</th>
                <th>Load(1m)</th>
                <th>CS</th>
                <th>Last Recv Time</th>
                <th>Manage</th>
            </tr>
            </thead>
            <tbody>
            <tr v-for="a in agents">
                <td><router-link :to="{name: 'node', params: {aid:a.aid}}">{{a.name}}</router-link></td>
                <td>
                        <span class="label"
                              :class="{'label-success': a.status=='active', 'label-default': a.status=='inactive'}">
                        {{a.status}}
                        </span>
                </td>
                <td>{{a.host}}</td>
                <td>{{a.last_cpu_util || '-'}}</td>
                <td>{{a.last_mem_util || '-'}}</td>
                <td>{{a.last_sys_load1 || '-'}}</td>
                <td>{{a.last_sys_cs || '-'}}</td>
                <td>{{a.last_msg_at.fromNow()}}</td>
                <td>
                    <button class="btn btn-sm btn-warning" @click="refreshNode(a)">
                        <span class="glyphicon glyphicon-refresh" aria-hidden="true"></span>
                    </button>
                    <!--button class="btn btn-sm btn-info">
                        <span class="glyphicon glyphicon-edit" aria-hidden="true"></span>
                    </button-->
                    <button class="btn btn-sm btn-danger" @click="removeNode(a)">
                        <span class="glyphicon glyphicon-trash" aria-hidden="true"></span>
                    </button>
                </td>
            </tr>
            </tbody>
        </table>
        <div v-if="!agents || agents.length == 0" class="alert alert-warning">no agents</div>
    </div>
</template>

<script>
    import moment from 'moment'
    import NodeForm from './NodeForm'

    export default {
        data () {
            return {
                agents: null
            }
        },

        created: function() {
            this.loadAgents()
        },

        methods: {
            loadAgents: function() {
                var self = this;
                self.$http.get('/api/agents').then(resp => {
                    return resp.json()
                }).then(data => {
                    data.agents.forEach(function(ele) {
                        ele.last_msg_at = moment(ele.last_msg_at)
                    })
                    self.agents = data.agents
                    self.master_addr = data.master_addr
                })
            },

            addNode: function() {
                var self = this
                self.$modal.show(NodeForm, {
                    model: {
                        master_addr: self.master_addr,
                        connect_type: 'password',
                        username: 'root'
                    }
                }, {
                    height: 'auto'
                }, {
                    'before-close': (event) => { self.loadAgents() }
                })
            },

            refreshNode: function(agent) {
                var self = this
                agent.master_addr = self.master_addr
                agent.username = 'root'
                agent.connect_type = 'password'
                self.$modal.show(NodeForm, {
                    model: agent
                }, {
                    height: 'auto'
                }, {
                    'before-close': (event) => { self.loadAgents() }
                })
            },

            removeNode: function (agent) {
                var self = this
                agent.master_addr = self.master_addr
                agent.username = 'root'
                agent.connect_type = 'password'
                self.$modal.show(NodeForm, {
                    model: agent,
                    action: 'remove'
                }, {
                    height: 'auto'
                }, {
                    'before-close': (event) => { self.loadAgents() }
                })
            }
        }
    }
</script>