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
	    alert('Request error, please check console log.')
		console.error(jqXHR.responseText);
	}
})

/** Shortcut for ajax **/
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

	get: function(url, succ) {
	    this.doAjax(url,'GET', succ);
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
Vue.filter('percent', function(number) {
    return (number * 100) + '%'
});
Vue.filter('decimal', function(number, precision) {
    if (precision == undefined) {
        precision = 2
    }
    var pows = Math.pow(10, precision)
    var d = Math.round(number * pows) / pows
    return d;
});

/** common components**/
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

// Report toolbar
Vue.component("report-toolbar", {
    template: `
    <div>
        <label>{{title}}</label> 
        
        <div class="btn-group" role="group">
            <button class="btn btn-sm btn-default" :class="{'btn-primary': range == 'last_hour'}" 
                @click="changeRange('last_hour')">Last Hour</button>
            <button class="btn btn-sm btn-default" :class="{'btn-primary': range == 'last_day'}" 
                @click="changeRange('last_day')">Last Day</button>
            <button class="btn btn-sm btn-default" :class="{'btn-primary': range == 'last_week'}" 
                @click="changeRange('last_week')">Last Week</button>
        </div>
        
        <span><input type="text" placeholder="Start Time" size="8" style="text-align: center" v-model="startAtModel"/></span>
         - 
        <span><input type="text" placeholder="End Time" size="8" style="text-align: center" v-model="endAtModel"/></span>
        
        <button class="btn btn-sm btn-success" @click="reload()">Reload</button>
    </div>
    `,
    props: ['title'],
    data: function() {
        return {
            range: 'last_hour',
            startAt: moment().subtract(1, 'h'),
            startAtModel: null,
            endAt: moment(),
            endAtModel: null
        };
    },
    created: function() {
        this.changeRange(this.range)
    },
    watch: {
        startAt: function() {
            this.startAtModel = this.startAt.format('MM/DD HH:00')
        },
        endAt: function() {
            this.endAtModel = this.endAt.format('MM/DD HH:00')
        }
    },
    methods: {

        changeRange: function(range) {
            this.range = range
            this.startAt = moment()
            this.endAt = moment()
            switch (range) {
                case 'last_hour':
                    this.startAt.subtract(1, 'h')
                    break;
                case 'last_day':
                    this.startAt.subtract(24, 'h')
                    break;
                case 'last_week':
                    this.startAt.subtract(7, 'd')
                    break;
            }
            this.$emit('changeRange', this.startAt, this.endAt)
            console.log('change range of ' + this.title + ' to ' + this.startAt + ':' + this.endAt )
        },

        reload: function() {
            this.$emit("reload");
            console.log("reload data of " + this.title)
        }
    }
});


/**Echarts**/
function genChartOption(title, data, cateProp, seriesPropsMapping, options) {
    options = options || {}
    options.stack = options.stack || false
    options.yAxisFmt = options.yAxisFmt || '{value}'
    //options.yAxisMin
    //options.yAxisMax
    console.log('options for graph ' + title + ': ' + JSON.stringify(options))

    var category = []
    var seriesMap = {}
    var legends = []
    data.forEach(function(d) {
        var serieDataCatetory = d[cateProp]
        category.push(serieDataCatetory)
        for(var serieName in seriesPropsMapping) {
            var serie = seriesMap[serieName];
            if (!serie) {
                serie = {name: serieName, type: 'line', data: []};
                if(options.stack) {
                    serie.stack = 'Total';
                    serie.areaStyle = {normal: {}};
                }
                serie.markLine = options.markLine
                seriesMap[serieName] = serie;
            }
            var serieDataProp = seriesPropsMapping[serieName];
            var serieDataValue = d[serieDataProp]
            serie.data.push(serieDataValue)
        }
    })
    var series = [];
    for(serieName in seriesMap) {
        legends.push(serieName);
        series.push(seriesMap[serieName]);
    }

    return {
        title: {text: title},
        animation: false,
        tooltip: {
            trigger: 'axis'
        },
        legend: {
            data:legends
        },
        xAxis: {
            type: 'category',
            data: category,
            boundaryGap : false,
            axisLabel: {
                formatter: function(v, idx) {
                    return v.substr(5, v.length)
                }
            }
        },
        yAxis: {
            type: 'value',
            min: options.yAxisMin,
            max: options.yAxisMax,
            axisLabel: {
                formatter: options.yAxisFmt
            }
        },
        dataZoom: [{
            type: 'slider',
            xAxisIndex: [0],
            start: 0,
            end: 100
        }
        ],
        series: series
    }
}

