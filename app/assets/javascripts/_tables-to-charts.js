(function (GOVUK, GDM) {

    GOVUK.GDM.tablesToCharts = function () {

        var isBigScreen = $("#framework-statistics-big-screen").length,
            colourSequence = isBigScreen ?
                ['#55ffee', '#ffee55', '#ff55ee', '#90ff00']
                :
                ['#D53880', '#2B8CC4', '#6F72AF', '#F47738'],
            typeSequence = [
                "area", "area", "bar"
            ];

        $(".framework-statistics table")
            .each(function (tableIndex) {
                var chartConfig = {
                    bindto: '#chart-' + tableIndex,
                    legend: {
                        show: false
                    },
                    color: {
                        pattern: colourSequence
                    },
                    size: {
                        height: isBigScreen ? 320 : 480
                    },
                    tooltip: {
                        show: !isBigScreen
                    }
                };
                var columns = [], groups = [], types = {}, chartType = '';

                $("thead th", this).each(function (colIndex) {

                    var columnHeading = $.trim($(this).text());

                    chartType = typeSequence[tableIndex];

                    $(this).append("<span class='key' />");

                    $(".key", this).css(
                        "background", colourSequence[colIndex - 1]
                    );

                    columns.push([columnHeading]);

                    if (colIndex) {
                        if ("area" == chartType) {
                            groups.push(columnHeading);
                        }
                        if ("bar" == chartType && colIndex != 0) {
                            groups.push(columnHeading);
                        }
                        types[columnHeading] = chartType;
                    }

                });

                $(this).before($("<div class='statistics-chart' id='chart-" + tableIndex + "'/>"));

                $("tbody tr", this).each(function (rowIndex) {

                    $("td", this).each(function (colIndex) {
                        if ("bar" == chartType && colIndex == 0) {
                            groups.push($.trim($(this).text()));
                        }
                        columns[colIndex].push(
                            $.trim($(this).text())
                        );

                    });

                });

                if (chartType == 'bar') {
                    console.log(groups);
                    chartConfig['data'] = {
                        columns: columns,
                        groups: [groups],
                        type: 'bar'
                    };
                    chartConfig['axis'] = {
                        x: {
                            type: 'category',
                            categories: groups

                        }
                    };
                    var chart = c3.generate(chartConfig);
                } else {

                    chartConfig['data'] = {
                        x: "Date and time",
                        xFormat: "%Y/%m/%d %H:%M:%S",
                        columns: columns,
                        order: null,
                        types: types,
                        groups: [groups],
                    };
                    chartConfig['axis'] = {
                        x: {
                            type: 'timeseries',
                            tick: {
                                format: '%Y-%m-%d %H:%M:%S',
                                fit: false
                            },
                            show: false
                        },
                        y: {
                            show: false
                        }
                    };
                    var chart = c3.generate(chartConfig);
                }
                ;
            });
    };

}).apply(this, [GOVUK || {}, GOVUK.GDM || {}]);
