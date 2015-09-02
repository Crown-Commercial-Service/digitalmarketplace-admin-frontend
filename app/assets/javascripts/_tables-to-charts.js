(function(GOVUK, GDM) {

  GOVUK.GDM.tablesToCharts = function() {

    var isBigScreen = $("#framework-statistics-big-screen").length,
        colourSequence = isBigScreen ?
          ['#55ffee', '#ffee55', '#ff55ee', '#90ff00']
          :
          ['#D53880', '#2B8CC4', '#6F72AF', '#F47738'],
        typeSequence = [
          "area", "line", "area", "area"
        ];

    $(".framework-statistics table")
      .each(function(tableIndex) {

        var columns = [], groups = [], types = {};

        $("thead th", this).each(function(colIndex) {

          var columnHeading = $.trim($(this).text()),
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
            types[columnHeading] = chartType;
          }

        });

        $("tbody tr", this).each(function(rowIndex) {

          $("td", this).each(function(colIndex) {

            columns[colIndex].push(
              $.trim($(this).text())
            );

          });

        });

        $(this).before($("<div class='statistics-chart' id='chart-" + tableIndex + "'/>"));

        var chart = c3.generate({
            bindto: '#chart-' + tableIndex,
            data: {
              x: "Date and time",
              xFormat: "%Y/%m/%d %H:%M:%S",
              columns: columns,
              order: null,
              types: types,
              groups: [groups],
            },
            axis: {
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
            },
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
        });

      });

  };

}).apply(this, [GOVUK||{}, GOVUK.GDM||{}]);
