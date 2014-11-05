'use strict';

/*global beforeEach, afterEach */

var resetApp = require('./helpers/liveblog_fixtures').resetApp;

// runs before every spec
beforeEach(function(done) {
    // see https://github.com/angular/protractor/blob/master/docs/timeouts.md
    // if not using angular:
    //browser.ignoreSynchronization = true;
    // for angular:
    browser.get(protractor.getInstance().params.baseUrl);

    resetApp(function() {done();});
});

// runs after every spec
afterEach(function() {});
