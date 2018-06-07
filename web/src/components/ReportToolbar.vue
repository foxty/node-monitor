<template>
    <div>
        <label>{{title}}</label>

        <div class="btn-group" role="group">
            <button class="btn btn-sm btn-default"
                    @click="changeRange('last_hour')">Last Hour</button>
            <button class="btn btn-sm btn-default"
                    @click="changeRange('last_day')">Last Day</button>
            <button class="btn btn-sm btn-default"
                    @click="changeRange('last_week')">Last Week</button>
        </div>

        <span><input type="text" placeholder="Start Time" size="10" style="text-align: center" v-model="startAt"/></span>
        -
        <span><input type="text" placeholder="End Time" size="10" style="text-align: center" v-model="endAt"/></span>

        <button class="btn btn-sm btn-success" @click="reload()">Reload</button>
    </div>
</template>

<script>
    import moment from 'moment'

    export default {

        props: ['title'],
        data: function() {
            return {
                fmt: 'YY/MM/DD HH:mm',
                startAt: moment().subtract(1, 'h'),
                endAt: moment(),
            };
        },
        created: function() {
            this.changeRange('last_hour')
        },
        watch: {
            startAt: function() {
            },
            endAt: function() {
            },

        },
        methods: {

            changeRange: function(range) {
                const start = moment()
                const end = moment()
                switch (range) {
                    case 'last_hour':
                        start.subtract(1, 'h')
                        break;
                    case 'last_day':
                        start.subtract(24, 'h')
                        break;
                    case 'last_week':
                        start.subtract(7, 'd')
                        break;
                }
                this.startAt = start.format(this.fmt)
                this.endAt = end.format(this.fmt)
                this.$emit('changeRange', start, end)
                console.log('change range of ' + this.title + ' to ' + this.startAt + ':' + this.endAt )
            },

            reload: function() {
                const start = moment(this.startAt, this.fmt)
                const end = moment(this.endAt, this.fmt)
                this.$emit('changeRange', start, end)
                console.log("reload data of " + this.title + ' to ' + this.startAt + ':' + this.endAt)
            }
        }
    }
</script>