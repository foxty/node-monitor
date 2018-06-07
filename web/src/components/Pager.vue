<template>
    <div class="pagination pagination-centered" style="clear:both;">
        <ul><li :class="{disabled:pagination.page<=1}"><a @click="to(pagination.page-1)">上一页</a></li>
            <li v-for="p in pages"><a href="javascript:void(0);" @click="to(p)">{{p}}</a></li>
            <li :class="{disabled:pagination.page >= pagination.maxPage}"><a @click="to(pagination.page+1)">下一页</a></li>
        </ul></div>
</template>

<script>
    export default {
        props: ['pagination'],
        data: function() {
            var page = this.pagination.page;
            var maxPage = this.pagination.maxPage
            var factor = parseInt(page / 10);
            var startPage = factor * 10 + 1;
            var endPage = Math.min(maxPage, factor * 10 + 10);
            var pages = [];
            for(var p = startPage; p <= endPage; p ++) {
                pages.push(p);
            }
            return {pages:pages}
        },
        methods: {
            to: function(page) {
                if (page >= 1 && page <= this.pagination.maxPage) {
                    this.$emit("to", page);
                } else {
                    console.warn("Invalid page " + page);
                }
            }
        }
    }
</script>
