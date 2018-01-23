/**jQuery Defaults**/
$(document).ajaxStart(function() {
	console.log('ajax start...')
}).ajaxStop(function(){
	console.log('ajax stop.')
}).ajaxError(function (event, jqXHR, ajaxSettings, error){
	var ct = jqXHR.getResponseHeader("Content-Type");
	if(/application\/json/.test(ct)) {
		alert(jqXHR.responseText);
	} else {
		console.error(jqXHR.responseText);
	}
})

// Shortcut for ajax calls
var Ajax = {
	
	doAjax: function(url, method, data, succ) {
		if(typeof(data) == 'function' && succ == undefined) {
			succ = data;
		}
		$.ajax({
		    url: url,
		    type: method,
		    data: data,
		    dataType: "json",
		    success: succ
		});
	},

	post: function(url, data, succ) {
		this.doAjax(url, "POST", data, succ);
	},
	
	put: function(url, data, succ) {
		this.doAjax(url, "PUT", data, succ);
	},
	
	delete: function(url, succ) {
		this.doAjax(url, "DELETE", null, succ);
	}
}

/**Plugins**/

/**Filters**/
Vue.filter('howLongAgo', function(date) {
	var result = "还未";
	if(date) {
		var curTime = new Date().getTime();
		var gap = curTime - date;
		var minutes = parseInt(gap / (1000 * 60));
		if (minutes / (60 * 24) > 1) {
			result = parseInt(minutes / (60 * 24)) + "天前";
		} else if (minutes / 60 > 1) {
			result = parseInt(minutes / 60) + "小时前";
		} else if (minutes > 0) {
			result = minutes + "分钟前";
		} else {
			result = "刚刚";
		}
	}
	return result;
});
Vue.filter('datePrint', function(millis) {
	var date = new Date(millis);
	return (date.getYear() + 1900) + "-" + (date.getMonth() + 1) + "-" + date.getDate();
});


/**Components**/
Vue.component('pager', {
	template: '<div class="pagination pagination-centered" style="clear:both;">\
		<ul><li :class="{disabled:pagination.page<=1}"><a @click="to(pagination.page-1)">上一页</a></li>\
		<li v-for="p in pages"><a href="javascript:void(0);" @click="to(p)">{{p}}</a></li>\
		<li :class="{disabled:pagination.page >= pagination.maxPage}"><a @click="to(pagination.page+1)">下一页</a></li>\
		</ul></div>',
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
});

// In-place Editor
Vue.component("v-ipe", {
	template: '{{content}}',
	props: ['content'],
	data: function() {
		return {}
	},
	methods: {		
	}
});

// Window
Vue.component("v-window", {
	template: "<div v-if='on'>" +
			"<div style='position:absolute;top:0;left:0;background-color:#666;opacity:0.5;width:100%;height:100%;z-index:100;'></div>" +
			"<div style='position:absolute;padding:10px;border:1px solid #999;background-color:#fff;z-index:110;" +
			"-webkit-border-radius:4px;-moz-border-radius:4px;border-radius:4px;width:{{w}}px;min-width:320px;'>" +
			"<span style='float:right;'><a @click='closeIt'>X</a></span>" +
			"<h4 v-if='title' style='margin:0;border-bottom:1px solid #D2B48C;padding:0 0 5px 10px;'>{{title}}</h4>" +
			"<div style='padding:5px 5px 5px 10px;'><slot>NO CONTENT!</slot></div>" +
			"</div>" +
			"</div>",
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
});

/**Vue Apps**/

function navi(ele) {
    return new Vue({
    		el: ele,
    		data: {
    		    curIndex: 0
    		},

    		created: function() {
    		    this.apps = [dashboard("#dashboard-app"),
    		                nodes("#nodes-app"),
    		                alarms("#alarms-app"),
    		                settings("#settings-app")]
    		},

    		methods: {
                enableApp: function(idx) {
                    app = this.apps[idx]
                    this.apps.forEach(function(app, index) {
                        app.enabled = idx == index;
                    })
                    this.curIndex = idx;
                }
    		}
    	});
}

function dashboard(ele) {
	return new Vue({
		el: ele,
		data: {
		    title:'Dashboard',
		    enabled: false
		},
		
		computed: {
		},
		
		created: function() {
		},
		
		methods: {

		}
	});
}

function nodes(ele) {
	return new Vue({
		el: ele,
		data: {
		    title:'Node List',
		    enabled: false
		},

		computed: {
		},

		created: function() {
		},

		methods: {

		}
	});
}

function alarms(ele) {
	return new Vue({
		el: ele,
		data: {
		    title:'Alarms',
		    enabled: false
		},

		computed: {
		},

		created: function() {
		},

		methods: {

		}
	});
}

function settings(ele) {
	return new Vue({
		el: ele,
		data: {
		    title:'Settings',
		    enabled: false
		},

		computed: {
		},

		created: function() {
		},

		methods: {

		}
	});
}