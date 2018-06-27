/*
Common libs
 */


// parse json
const DATETIME_RE = /^\d{4}-\d{1,2}-\d{1,2}T\d{2}:\d{2}:\d{2}Z$/
const parseJson = function(text) {
    JSON.parse(text, (key, value) => {
        typeof value == 'string' && DATETIME_RE.test(value) ? new Date(value) : value
    })
}

/**Echarts**/
const genChartOption = function (title, data, cateProp, seriesPropsMapping, options) {
    options = options || {}
    options.stack = options.stack || false
    options.yAxisFmt = options.yAxisFmt || '{value}'
    //options.yAxisMin
    //options.yAxisMax
    console.log('options for graph ' + title + ': ' + JSON.stringify(options))

    var category = []
    var seriesMap = {}
    var legends = []
    data.forEach(function (d) {
        var serieCategory = d[cateProp]
        serieCategory = typeof serieCategory == 'string' && DATETIME_RE.test(serieCategory)
            ? new Date(serieCategory)
            : serieCategory
        category.push(serieCategory)
        for (var serieName in seriesPropsMapping) {
            var serie = seriesMap[serieName];
            if (!serie) {
                serie = {name: serieName, type: 'line', data: []};
                if (options.stack) {
                    serie.stack = 'Total';
                    serie.areaStyle = {normal: {}};
                }
                serie.markLine = options.markLine
                seriesMap[serieName] = serie;
            }
            var serieDataProp = seriesPropsMapping[serieName];
            var serieDataValue = d[serieDataProp]
            serie.data.push([serieCategory, serieDataValue])
        }
    })
    var series = [];
    for (var serieName in seriesMap) {
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
            data: legends
        },
        xAxis: {
            type: 'time',
            data: category,
            boundaryGap: false
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

export {genChartOption}