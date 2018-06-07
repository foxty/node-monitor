<template>
    <div>
        <div class="col-md-2" style="width:140px;">
            <ul class="nav nav-pills nav-stacked">
                <li role="presentation" :class="{'active': $route.name == 'nodeStatus'}">
                    <router-link :to="{name: 'nodeStatus', params: {aid:aid}}">
                        <span class="glyphicon glyphicon-signal" aria-hidden="true"></span>
                        Status
                    </router-link>
                </li>
                <li role="presentation"
                    :class="{'active': $route.name == 'nodeServices' || $route.name.startsWith('service')}">
                    <router-link :to="{name: 'nodeServices', params: {aid:aid}}">
                        <span class="glyphicon glyphicon-th-large" aria-hidden="true"></span>
                        Service
                    </router-link>
                </li>
            </ul>
        </div>
        <div class="col-md-10">
            <div class="alert alert-info">Node {{agent ? agent.name + '@' + agent.host : ''}}</div>
            <router-view></router-view>
        </div>
    </div>
</template>

<script>
    import {Ajax} from '../common'

    export default {
        props: ['aid'],

        data: function () {
            return {
                agent: null
            }
        },

        created: function () {
            this.loadData();
            // set default tab
            if (this.$route.name == 'node') this.$router.push({name: 'nodeStatus'})
        },

        methods: {
            loadData: function () {
                var self = this;
                var aid = self.aid;
                Ajax.get(`/api/agents/${aid}`, function (agent) {
                    self.agent = agent
                })
            },

            showServiceStatus: function (serviceId) {
                this.curServiceId = serviceId
            }
        }
    }
</script>

<style>
</style>