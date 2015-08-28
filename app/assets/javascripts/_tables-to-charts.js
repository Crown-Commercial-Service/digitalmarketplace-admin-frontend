(function(GOVUK, GDM) {

  GOVUK.GDM.tablesToCharts = function() {

    $(".framework-statistics table")
      .each(function(tableIndex) {

        var columns = [];

        $("thead th", this).each(function(colIndex) {
          console.log($.trim($(this).text()));
          columns.push([
            $.trim($(this).text())
          ]);
        });

        $("tbody tr", this).each(function(rowIndex) {

          $("td", this).each(function(colIndex) {

            columns[colIndex].push(
              $.trim($(this).text())
            );

          });

        });

        $(this).before($("<div id='chart-" + tableIndex + "'/>"));

        console.log(columns);

        var chart = c3.generate({
            bindto: '#chart-' + tableIndex,
            data: {
              x: "Date and time",
              xFormat: "%Y-%m-%dT%H:%M",
              columns: columns
            },
            axis: {
              x: {
                type: 'timeseries',
                tick: {
                  format: '%Y-%m-%d'
                },
                show: false
              },
              y: {
                show: false
              }
            },
            legend: {
              show: false
            }
        });

      });

  };

}).apply(this, [GOVUK||{}, GOVUK.GDM||{}]);
