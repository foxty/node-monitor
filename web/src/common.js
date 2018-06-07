/*
Common libs
 */
import $ from 'jquery';

const Ajax = {
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

/**Echarts**/
const genChartOption = function(title, data, cateProp, seriesPropsMapping, options) {
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
    for(var serieName in seriesMap) {
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

export { Ajax, genChartOption }