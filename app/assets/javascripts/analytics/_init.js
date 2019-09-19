// Custom Admin FE analytics
//= include _register.js

// DM Frontend Toolkit analytics
//= include ../../../../node_modules/digitalmarketplace-frontend-toolkit/toolkit/javascripts/analytics/_pii.js
//= include ../../../../node_modules/digitalmarketplace-frontend-toolkit/toolkit/javascripts/analytics/_googleAnalyticsUniversalTracker.js
//= include ../../../../node_modules/digitalmarketplace-frontend-toolkit/toolkit/javascripts/analytics/_govukAnalytics.js
//= include ../../../../node_modules/digitalmarketplace-frontend-toolkit/toolkit/javascripts/analytics/_events.js
//= include ../../../../node_modules/digitalmarketplace-frontend-toolkit/toolkit/javascripts/analytics/_pageViews.js
//= include ../../../../node_modules/digitalmarketplace-frontend-toolkit/toolkit/javascripts/analytics/_virtualPageViews.js
//= include ../../../../node_modules/digitalmarketplace-frontend-toolkit/toolkit/javascripts/analytics/_trackExternalLinks.js

(function(root) {
  "use strict";
  root.GOVUK.GDM.analytics.init = function () {
    this.register();
    this.pageViews.init();
    this.events.init();
    this.virtualPageViews();
    this.trackExternalLinks.init();
  };
})(window);
