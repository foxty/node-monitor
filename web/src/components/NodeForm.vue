<template>
    <form class="form-horizontal" style="margin:30px">
        <div class="form-group" v-if="agent.aid">
            <label class="col-sm-3 control-label">Node ID</label>
            <div class="col-sm-9">
                <input type="text" disabled="disabled" class="form-control" v-model="agent.aid">
            </div>
        </div>
        <div class="form-group">
            <label for="node_host" class="col-sm-3 control-label">Node Host</label>
            <div class="col-sm-9">
                <input type="text" v-bind:disabled="action=='remove'" class="form-control" id="node_host" placeholder="host or ip" v-model="agent.host">
            </div>
        </div>
        <div class="form-group" v-if="action != 'remove'">
            <label for="master_addr" class="col-sm-3 control-label">Master Host</label>
            <div class="col-sm-9">
                <input type="text" class="form-control" id="master_addr" placeholder="x.x.x.x:30079" v-model="agent.master_addr">
            </div>
        </div>
        <div class="form-group">
            <label class="col-sm-3 control-label">Connect Type</label>
            <div class="col-sm-9">
                <label class="radio-inline">
                    <input type="radio" name="connect_type" value="password" v-model="agent.connect_type">Password SSH
                </label>
                <label class="radio-inline">
                    <input type="radio" name="connect_type" value="passwordless" v-model="agent.connect_type">Passwordless SSH
                </label>
            </div>
        </div>

        <div v-if="agent.connect_type == 'password'">
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
        <div v-else class="form-group">
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
        props: ['model', 'action'],
        data: function () {
            return {
                agent: this.model
            }
        },
        methods: {
            submit: function() {
                console.log('submit agent ' + JSON.stringify(this.agent))
                this.action == 'remove' ? this.removeNode() : this.installNode()
            },

            installNode: function() {
                let self = this
                if (self.agent) {
                    self.$http.post('/api/agents', self.agent).then(resp => {
                        self.$emit('close')
                        self.$modal.show('dialog', {
                            title: 'Success',
                            text: 'Node ' + self.agent.host + ' has been setup, please wait few seconds for update.',
                        })
                    }, resp => {
                        self.$emit('close')
                    })
                }
            },
            
            removeNode: function () {
                let self = this;
                let params = {
                    connect_type: self.agent.connect_type,
                    username: self.agent.username,
                    password: self.agent.password
                }
                self.$http.delete(`/api/agents/` + self.agent.aid, {params: params}).then(resp => {
                    return resp.json()
                }, resp => {
                    self.$emit('close')
                }).then(data => {
                    self.$emit('close')
                    console.log('agent ' + data.name + ' was removed.')
                })
            }
        }
    }
</script>