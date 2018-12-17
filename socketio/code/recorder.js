'use strict';

const bindings = require('bindings');

let recorderAddOn;

const print = (stuff) => { console.log('recorderAddOn: ' + stuff + '\n'); };

try { recorderAddOn = bindings('recorder'); }
catch (e) {
    recorderAddOn = undefined;
    print('bindings failed: ' + e);
};

const test = () => {
    if (recorderAddOn) { print('hello ' + recorderAddOn.hello()); }
    else { print('not available'); }
};

const Recorder = function (settings) {
    const theThis = this; if (!(theThis instanceof Recorder)) { return new Recorder(settings); };
    let recorderUse;

    this.analyse_frame = (binaryData, then) => {
        if (recorderUse) {
            recorderUse.analyse_frame(
                (result) => {
                    then(result);
                    //if (result && result.length) { print('analyse_frame result: ' + JSON.stringify(result)); }
                },
                binaryData);
        }
    };

    this.start_frame_data = (outputFileName, width, height) => {
        if (recorderUse) {
            recorderUse.start_frame_data(
                (result) => {
                    //print('start_frame_data result: ' + result);
                },
                outputFileName, width, height);
        }
    };

    this.end_frame_data = (outputFileName, then) => {
        if (recorderUse) {
            recorderUse.end_frame_data(
                (result) => {
                    //print('end_frame_data result: ' + result);
                    then();
                },
                outputFileName);
        }
    };

    this.set_frame_data = (outputFileName, binaryData, millisInVideo) => {
        if (recorderUse) {
            recorderUse.set_frame_data(
                (result) => {
                    //print('set_frame_data result: ' + result);
                },
                outputFileName, binaryData, millisInVideo);
        }
    };

    const initialize = () => {
        recorderUse = recorderAddOn;
        //recorderUse = undefined;
    };

    initialize();
};

const recorder = Recorder({});

module.exports = {
    test: test,
    recorder: recorder
};
