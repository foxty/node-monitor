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

const convertBytes = function(value, from, to) {
    
}

const tsFormatter = function(ts) {
    let d = new Date(ts)
    return (d.getMonth() + 1) + "/" + d.getDate() + " "
        + d.getHours() + ":" + d.getMinutes()
}

/**Echarts**/
const genChartOption = function (title, data, seriesMapping, options) {
    options = options || {}
    options.stack = options.stack || false
    options.yAxisFmt = options.yAxisFmt || '{value}'
    //options.yAxisMin
    //options.yAxisMax
    console.log('options for graph ' + title + ': ' + JSON.stringify(options))

    let legends = []
    let series = []
    for (let serieName in seriesMapping) {
        legends.push(serieName)
        let serieKey = seriesMapping[serieName]
        let metric = data[serieKey]
        if (!metric || metric.length ==0) {
            console.warn('no metric data for ' + serieKey)
            continue
        }
        let dps = metric[0].dps
        let serieData = []
        for (let ts in dps) {
            serieData.push([ts*1000, Math.round(dps[ts]*100)/100])
        }
        let serie = {
            name: serieName,
            type: 'line',
            showSymbol: false,
            data: serieData
        };
        if (options.stack) {
            serie.stack = true;
            serie.areaStyle = {normal: {}};
        }
        serie.markLine = options.markLine
        series.push(serie)
    }

    let go = {
        title: {text: title},
        tooltip: {
            trigger: 'axis',
            formatter: function (params) {
                let label =  tsFormatter(params[0].axisValue)
                label += '<ul style="list-style-type:square; margin:0;padding-left:20px">'
                params.forEach( param => {
                    label += '<li style="color:'+param.color+'">'
                        + '<span style="color:white">'
                        + param.seriesName
                        + ' : '
                        + param.value[1]
                        + '</span></li>'
                })
                return label + '</ul>'
            }
        },
        legend: {
            data: legends
        },
        xAxis: {
            type: 'category',
            boundaryGap: false,
            axisLabel: {
                formatter: tsFormatter
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
    console.debug(go)
    return go;
}

export {genChartOption}