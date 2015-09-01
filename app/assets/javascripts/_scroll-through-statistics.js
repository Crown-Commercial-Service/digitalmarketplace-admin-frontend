(function(GOVUK, GDM) {

  var $page = $("html, body"),
      delayInSeconds = 16,
      generateScrollTo = function($sections, index) {

        return function() {

          scrollPage($sections.eq(index).offset().top);

          setTimeout(
            generateScrollTo(
              $sections, (index + 1 == $sections.length) ? 0 : ++index
            ),
            delayInSeconds * 1000
          );

        };

      },
      scrollPage = function(offset) {

        $page.animate({
          scrollTop: offset
        });

      };

  GOVUK.GDM.scrollThroughStatistics = function() {

    if (!$("#framework-statistics-big-screen").length) return;

    setTimeout(function() {
      location.reload();
    }, 5 * 60 * 1000); // 5 minutes

    generateScrollTo(
      $("#framework-statistics-big-screen .summary-item-heading"), 0
    )();

  };

}).apply(this, [GOVUK||{}, GOVUK.GDM||{}]);
