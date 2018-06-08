<template>
    <form class="form-horizontal" style="margin:30px">
        <div class="form-group">
            <label for="nodeHost" class="col-sm-3 control-label">Node Host</label>
            <div class="col-sm-9">
                <input type="text" class="form-control" id="nodeHost" placeholder="host or ip" v-model="agent.host">
            </div>
        </div>
        <div class="form-group">
            <label for="masterHost" class="col-sm-3 control-label">Master Host</label>
            <div class="col-sm-9">
                <input type="text" class="form-control" id="masterHost" placeholder="x.x.x.x:30079" v-model="agent.masterHost">
            </div>
        </div>
        <div class="form-group">
            <label class="col-sm-3 control-label">Connect Type</label>
            <div class="col-sm-9">
                <label class="radio-inline">
                    <input type="radio" name="connectType" id="connectType1" value="password" v-model="agent.connectType">Password SSH
                </label>
                <label class="radio-inline">
                    <input type="radio" name="connectType" id="connectType2" value="passwordless" v-model="agent.connectType">Passwordless SSH
                </label>
            </div>
        </div>
        <div v-if="agent.connectType == 'password'">
            <div class="form-group">
                <label for="username" class="col-sm-3 control-label">User</label>
                <div class="col-sm-9">
                    <input type="text" class="form-control" id="username" placeholder="username for SSH" v-model="agent.username">
                </div>
            </div>
            <div class="form-group">
                <label for="password" class="col-sm-3 control-label">Password</label>
                <div class="col-sm-9">
                    <input type="text" class="form-control" id="password" placeholder="password for SSH" v-model="agent.password">
                </div>
            </div>
        </div>
        <div class="form-group" v-if="agent.connectType == 'passwordless'">
            <div class="alert alert-info">Please make sure passwordless access was setup from master to {{agent.host || 'node'}}.</div>
        </div>
        <div class="form-group">
            <div class="col-sm-offset-3 col-sm-9">
                <button type="button" class="btn btn-success" @click="submit">Submit</button>
                <button type="reset" class="btn btn-default" @click="$emit('close')">Cancel</button>
            </div>
        </div>
    </form>
</template>

<script>
    export default {
        name: 'NodeForm',
        props: ['model'],
        data: function () {
            return {
                agent: this.model || {}
            }
        },
        created: function () {
            agent.connectType = 'password'
        },
        methods: {
            submit: function() {
                let self = this
                console.log('submit agent ' + JSON.stringify(this.agent))
                if (self.agent) {
                    self.$http.post('/api/agents', self.agent).then(resp => {
                        console.log(resp)
                    })
                }
            }
        }
    }
</script>