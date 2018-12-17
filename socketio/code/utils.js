const child_process = require('child_process')
const fs = require('fs-extra');

const print = (stuff) => { console.log('utils: ' + stuff + '\n'); };

const getTimeStampFromDate = (date) => {
    let timeStampStr;
    if (!!date) {
        let year = date.getFullYear();
        let month = date.getMonth() + 1;
        let day = date.getDate();
        let hours = date.getHours();
        let minutes = date.getMinutes();
        let seconds = date.getSeconds();
        if (month < 10) { month = '0' + month; }
        if (day < 10) { day = '0' + day; }
        if (hours < 10) { hours = '0' + hours; }
        if (minutes < 10) { minutes = '0' + minutes; }
        if (seconds < 10) { seconds = '0' + seconds; }
        timeStampStr = '' + year + '-' + month + '-' + day + ' ' + hours + ':' + minutes + ':' + seconds + '.0';
    }
    return timeStampStr;
};

const getTimestampNow = () => { return (new Date()).toISOString(); };
const getTimestampFromMillis = millis => { return new Date(millis).toISOString(); };

const makeURLParams = data => {
    let params = "";
    for (let i in data) {
        if (params.length) { params += '&'; }
        params += i + '=' + encodeURIComponent(data[i]);
    }
    return params;
};

const deleteFolderRecursive = path => {
    try {
        if (fs.existsSync(path)) {
            fs.readdirSync(path).forEach(function (file, index) {
                let curPath = path + "/" + file;
                if (fs.statSync(curPath).isDirectory()) { deleteFolderRecursive(curPath); } else { fs.unlinkSync(curPath); }
            });
            fs.rmdirSync(path);
        }
    }
    catch (e) { print('deleteFolderRecursive exception: ' + e.message); }
};

const ffmpeg = (old_folder_name, index_file_name, output_file_name, then) => {
    let spawn = child_process.spawn;
    let cmd = '/usr/bin/ffmpeg';
    let args = ['-y', '-f', 'concat', '-i', index_file_name, output_file_name];
    print('ffmpeg: start process video ' + output_file_name + ' ' + getTimestampNow());
    var proc = spawn(cmd, args);
    proc.stdout.on('data', function (data) {
        //print(data + ' ' + outputFileName);
    });
    proc.stderr.on('data', function (data) {
        //print('ffmpeg: stderr: ' + data + ' ' + output_file_name);
    });
    proc.on('close', function () {
        //deleteFolderRecursive(old_folder_name);
        try { then(); } catch (e) { print('ffmpeg: then exception' + e.message); }
        print('ffmpeg: end process video ' + output_file_name + ' ' + getTimestampNow());
    });
};

const VIDEO_SERVER = process.env.VIDEO_SERVER || 'video';
const VIDEO_RTMP_PORT = process.env.VIDEO_RTMP_PORT || '1935';

const ffmpeg_rtmp_base_url = 'rtmp://' + VIDEO_SERVER + ':' + VIDEO_RTMP_PORT + '/live/';

const SOCKETIO_PORT = process.env.SOCKETIO_PORT || '1337';
const SOCKETIO_HOST = process.env.SOCKETIO_SERVER || 'socketio';

const socketio_last_frame_base_url = 'http://' + SOCKETIO_HOST + ':' + SOCKETIO_PORT + '/last_frame?id=';

const ffmpeg_rtmp = function (settings) {
    let theThis; if (!((theThis = this) instanceof ffmpeg_rtmp)) { return new ffmpeg_rtmp(settings); };
    let child;

    this.Kill = () => { if (child) { child.kill(); child = undefined; } };

    const initialize = () => {
        let spawn = child_process.spawn;
        let cmd = '/usr/bin/ffmpeg';

//ffmpeg -re -loop 1 -f image2 -i 'http://localhost:1337/last_frame?id=_DNMUnQ7LYlZ6AaAAAAB -c:v libx264 -tune zerolatency -preset veryfast -r 25 -maxrate 3000k -bufsize 6000k -pix_fmt yuv420p -g 25 -f flv rtmp://video:1935/live/test

        let last_frame_id = settings.id;
        let inputURL = socketio_last_frame_base_url + last_frame_id;
        let outputURL = ffmpeg_rtmp_base_url + last_frame_id;
        //let inputURL = 'http://localhost:1337/last_frame?id=' + last_frame_id;
        //let outputURL = 'rtmp://video:1935/live/' + last_frame_id;

        let args = ['-y', '-re', '-loglevel', 'quiet', '-loop', '1', '-f', 'image2', '-i', inputURL, '-c:v',
            'libx264', '-tune', 'zerolatency', '-preset', 'veryfast', '-r', '25', '-maxrate', '3000k', '-bufsize',
            '6000k', '-pix_fmt', 'yuv420p', '-g', '25', '-f', 'flv', outputURL
        ];

        print('ffmpeg_rtmp start ' + last_frame_id + ': ' + getTimestampNow());

        child = spawn(cmd, args);
        child.stdout.on('data', function (data) {
            //print('ffmpeg_rtmp: ' + data);
        });
        child.stderr.on('data', function (data) {
            //print('ffmpeg_rtmp: stderr: ' + data);
        });
        child.on('close', function () {
            child = undefined;
            print('ffmpeg_rtmp: end ' + last_frame_id + ': ' + getTimestampNow());
        });
    };
    initialize();
};

// cat /dev/stdin | ffmpeg -safe 0 -protocol_whitelist file,pipe -f concat -i pipe: test.mp4

const FFMpegPipe = function (settings) {
    let theThis; if (!((theThis = this) instanceof FFMpegPipe)) { return new FFMpegPipe(settings); };
    let child;

    this.IsOpen = () => { return child !== undefined; };
    this.GetSettings = () => { return settings; };
    this.WriteStdin = (content) => { if (child) { child.stdin.write(content); } };
    this.CloseStdin = () => {
        if (child) {
            print('CLOSING STDIN!!');
            child.stdin.end();
        }
    };

    const initialize = () => {
        if (settings && settings.output_file_name && settings.output_file_name.length) {
            let output_file_name = settings.output_file_name;
            print('ffmpegPIPE Init! ' + output_file_name);
            let cmd = '/usr/bin/ffmpeg';
            let args = ['-y', '-safe', '0', '-protocol_whitelist', 'file,pipe', '-f', 'concat', '-i', 'pipe:', output_file_name];
            print('ffmpeg: start process video ' + output_file_name + ' ' + getTimestampNow());
            child = child_process.spawn(cmd, args);
            child.stdin.setEncoding = settings.encoding !== undefined ? settings.encoding : 'utf-8';
            child.stdout.on('data', function (data) {
                print('ffmpegPIPE Data: ' + data);
            });
            child.stderr.on('data', function (data) {
                print('ffmpegPIPE err Data: ' + data);
            });
            child.on('close', function () {
                print('ffmpegPIPE on close! ' + output_file_name);
                //deleteFolderRecursive(old_folder_name);
                try { settings.then({ sender: theThis }); } catch (e) { print('FFMpegPipe: then exception' + e.message); }
                child = undefined;
                print('FFMpegPipe: end process video ' + output_file_name + ' ' + getTimestampNow());
            });
        }
    };

    initialize();
};

const SpawnPipe = function (settings) {
    let theThis; if (!((theThis = this) instanceof SpawnPipe)) { return new SpawnPipe(settings); };
    let child, openStdIn;

    this.IsOpen = () => { return openStdIn !== undefined; };
    this.GetSettings = () => { return settings; };
    this.WriteStdin = (content) => { if (openStdIn) { child.stdin.write(content); } };
    this.CloseStdin = () => {
        if (openStdIn) { openStdIn = false; if (settings.stdout) { print('SpawnPipe closing stdin'); } child.stdin.end(); }
    };

    const initialize = () => {
        if (settings) {
            try {
                let cmd = settings.cmd;
                let args = settings.args;
                //print('SpawnPipe init cmd is ' + settings.cmd + ' @ ' +  + getTimestampNow());
                child = child_process.spawn(cmd, args);
                child.stdin.setEncoding = settings.encoding !== undefined ? settings.encoding : 'utf-8';
                child.stdout.on('data', function (data) {
                    if (settings.stdout) { print('SpawnPipe: ' + data); }
                });
                child.stderr.on('data', function (data) {
                    if (settings.stderr) { print('SpawnPipe err: ' + data); }
                });
                child.on('close', function () {
                    openStdIn = false;
                    if (settings.stdout) { print('SpawnPipe on close'); }
                    try { settings.then({ sender: theThis }); } catch (e) { print('SpawnPipe: "then" exception' + e.message); }
                    child = undefined;
                    if (settings.stdout) { print('SpawnPipe after then'); }
                });
                openStdIn = true;
            }
            catch (e) {
                print('SpawnPipe exception: ' + e.message);
                child = undefined;
            };
        }
    };

    initialize();
};

const SpawnPipeMap = function (settings) {
    let theThis; if (!((theThis = this) instanceof SpawnPipeMap)) { return new SpawnPipeMap(settings); };
    let map;

    this.GetSettings = () => settings;
    this.Add = (key, spawnPipeSettings) => { theThis.Del(key); if (key && key.length) { map[key] = SpawnPipe(spawnPipeSettings); } };
    this.Del = (key) => { if (theThis.Get(key) !== undefined) { delete map[key]; } };
    this.Get = (key) => { return map[key]; };

    const initialize = () => { map = {}; };

    initialize();
};

module.exports = {
    getTimeStampFromDate: getTimeStampFromDate,
    makeURLParams: makeURLParams, deleteFolderRecursive: deleteFolderRecursive,
    getTimestampNow: getTimestampNow,
    getTimestampFromMillis: getTimestampFromMillis,
    ffmpeg: ffmpeg,
    ffmpeg_rtmp: ffmpeg_rtmp,
    FFMpegPipe: FFMpegPipe,
    SpawnPipe: SpawnPipe,
    SpawnPipeMap: SpawnPipeMap
};
