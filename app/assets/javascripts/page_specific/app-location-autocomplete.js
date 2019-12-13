;(function() {

  "use strict";

  var CountryAutocomplete = function() {

    openregisterLocationPicker({
      selectElement: document.getElementById('input-country'),
      url: '/admin/static/location-autocomplete-graph.json'
    });

    $('#input-country').keyup(function(event) {
      // Clear the input value of the country select input, if the autocomplete is cleared.
      if ($(this).val().length < 2) {
        $('#input-country-select').val('');
      };
    });
  };

  CountryAutocomplete();
})();
