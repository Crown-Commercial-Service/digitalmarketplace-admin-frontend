/*
  The following comments are parsed by Gulp include
  (https://www.npmjs.com/package/gulp-include) which uses
  Sprockets-style (https://github.com/sstephenson/sprockets)
  directives to concatenate multiple Javascript files into one.
*/
//= include ../../../node_modules/govuk_frontend_toolkit/javascripts/vendor/polyfills/bind.js
//= include ../../../bower_components/jquery/dist/jquery.js
//= include ../../../bower_components/hogan/web/builds/3.0.2/hogan-3.0.2.js
//= include ../../../bower_components/d3/d3.js
//= include ../../../bower_components/c3/c3.js
//= include ../../../bower_components/digitalmarketplace-frontend-toolkit/toolkit/javascripts/list-entry.js
//= include ../../../bower_components/digitalmarketplace-frontend-toolkit/toolkit/javascripts/word-counter.js
//= include ../../../node_modules/govuk_frontend_toolkit/javascripts/govuk/selection-buttons.js

; // JavaScript in the govuk_frontend_toolkit doesn't have trailing semicolons

//= include _selection-buttons.js
//= include _scroll-through-statistics.js
//= include _tables-to-charts.js
//= include ../../../bower_components/digitalmarketplace-frontend-toolkit/toolkit/javascripts/module-loader.js
