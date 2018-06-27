<template>
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
    </div>
</template>

<script>
    import moment from 'moment'
    export default {
        props: ['aid'],

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
            this.$router.push({name: 'serviceList'})
            this.$router.afterEach((to, from) => {
                self.curServiceId = to.params.service_id
            })
        },

        methods: {
            loadServices: function() {
                var self = this;
                var aid = self.aid
                self.$http.get(`/api/agents/${aid}/services`).then(resp => {
                    return resp.json()
                }).then(data => {
                    data.services.forEach(function(ele) {
                        ele.last_report_at = moment.utc(ele.last_report_at)
                    })
                    self.services = data.services;
                    self.services_status_map = data.services_status_map;
                })
            }
        }
    }
</script>

<style>
</style>