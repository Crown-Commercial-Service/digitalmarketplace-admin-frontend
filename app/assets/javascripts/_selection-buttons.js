(function(GOVUK, GDM) {

  GOVUK.GDM.selectionButtons = function() {

    if (!GOVUK.SelectionButtons) return;

    new GOVUK.SelectionButtons('.selection-button input');

    new GOVUK.ShowHideContent().init();

  };

}).apply(this, [GOVUK||{}, GOVUK.GDM||{}]);
