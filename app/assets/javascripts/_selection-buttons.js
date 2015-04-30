(function(GOVUK, GDM) {

  GOVUK.GDM.selectionButtons = function() {

    if (!GOVUK.SelectionButtons) return;

    new GOVUK.SelectionButtons('.selection-button input', {
      'focusedClass' : 'selection-button-focused',
      'selectedClass' : 'selection-button-selected'
    });

  };

}).apply(this, [GOVUK||{}, GOVUK.GDM||{}]);
