(function(GOVUK, GDM) {

  GOVUK.GDM.selectionButtons = function() {

    if (!GOVUK.SelectionButtons) return;

    new GOVUK.SelectionButtons('.selection-button input');

  };

}).apply(this, [GOVUK||{}, GOVUK.GDM||{}]);
