<template>
    <div v-if='on'>
        <div style='position:absolute;top:0;left:0;background-color:#666;opacity:0.5;width:100%;height:100%;z-index:100;'></div>
        <div style='position:absolute;padding:10px;border:1px solid #999;background-color:#fff;z-index:110;
    -webkit-border-radius:4px;-moz-border-radius:4px;border-radius:4px;width:{{w}}px;min-width:320px;'>
            <span style='float:right;'><a @click='closeIt'>X</a></span>
            <h4 v-if='title' style='margin:0;border-bottom:1px solid #D2B48C;padding:0 0 5px 10px;'>{{title}}</h4>
            <div style='padding:5px 5px 5px 10px;'>
                <slot>NO CONTENT!</slot>
            </div>
        </div>
    </div>
</template>

<script>
    export default {
        props: ["name", "on", "title", "w", "h"],
        data: function() {
            return {};
        },
        methods: {
            closeIt: function() {
                this.$emit("close");
                console.log("window " + this.name + " closed")
            }
        }
    }
</script>
