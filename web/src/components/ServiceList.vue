<template>
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
    </div>
</template>

<script>
    import {Ajax} from '../common'

    export default {
        props: ['aid', 'services', 'services_status_map'],

        data: function() {
            return {}
        },

        created: function() {
        },

        methods: {
        }
    }
</script>

<style>
</style>