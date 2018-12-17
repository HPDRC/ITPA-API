'use strict';

const SOCKETIO_TOKEN = process.env.SOCKETIO_TOKEN || '';
const SOCKETIO_PORT = process.env.SOCKETIO_PORT || '1337';
const SOCKETIO_HOST = '0.0.0.0';    // works, but should try with env name for socket io server

const ITPA_SERVER = process.env.ITPA_SERVER || 'itpa';
const ITPA_PORT = process.env.ITPA_PORT || '8060';
const ITPA_ADMIN_TOKEN = process.env.ITPA_ADMIN_TOKEN || '8060';
const ITPA_SERVER_URL = 'http://' + ITPA_SERVER + ':' + ITPA_PORT + '/';
const ITPA_USER_RIGHTS_URL = ITPA_SERVER_URL + 'user_rights?token=';

const API_SERVER = process.env.API_SERVER || 'api';
const API_PORT = process.env.API_PORT || '8000';
const API_SERVER_URL = 'http://' + API_SERVER + ':' + API_PORT + '/';

const API_TRACK_DEVICE_URL = API_SERVER_URL + 'itpa_track_device?';
const API_ADD_NEW_BUS_VIDEO_URL = API_SERVER_URL + 'add_new_bus_video?token=' + ITPA_ADMIN_TOKEN + '&';
const API_END_RECORD_BUS_VIDEO_URL = API_SERVER_URL + 'end_record_bus_video?token=' + ITPA_ADMIN_TOKEN + '&';

const REDIS_HOST = process.env.REDIS_HOST || 'cache';
const REDIS_PORT = process.env.REDIS_PORT || '6379';
const REDIS_PASSWORD = process.env.REDIS_PASSWORD || '';
const REDIS_DB = process.env.REDIS_DB || 0;

const cors = require('cors');

const fs = require('fs-extra');
const path = require('path');

const redis = require('redis');

const express = require('express');

const app = express();

const child_process = require('child_process');

const server = require('http').createServer(app);
const io = require('socket.io')(server, { path: '/socketio/socket.io' });

const print = (stuff) => { console.log(new Date().toISOString() +  ' server: ' + stuff + '\n'); };

const bodyParser = require('body-parser');

const Promise = require('bluebird');
const rp = require('request-promise');

const uuidv4 = require('uuid/v4');

const connection_ev = 'connection';
//const connected_ev = 'connected';
const disconnect_ev = 'disconnect';

const send_video_ev = 'send_video';
const receive_video_ev = 'receive_video';

const send_status_ev = 'send_status';
const end_send_ev = 'end_send';
//const receive_status_ev = 'receive_status';

const socket_rooms_data_change = 'socket_rooms';

const join_socket_room_ev = 'join_socket_room';
const leave_socket_room_ev = 'leave_socket_room';

const notify_data_change = 'notify_data_change';

const subscribe_data_change = 'subscribe_data_change';
const unsubscribe_data_change = 'unsubscribe_data_change';
const get_last_data_set = 'get_last_data_set';
const authentication_ev = 'authentication';
const authenticated_ev = 'authenticated';
const track_device_ev = 'itpa_track_device';

const utils = require('./utils');

const cv = require('/opencv4nodejs/node_modules/opencv4nodejs');
const frontalFaceAlt2Classifier = new cv.CascadeClassifier(cv.HAAR_FRONTALFACE_ALT2);
const profileFaceClassifier = new cv.CascadeClassifier('/opencv4nodejs/node_modules/opencv4nodejs/lib/haarcascades/haarcascade_profileface.xml');

//print('cascade location: ' + cv.HAAR_FRONTALFACE_ALT2);

const recorder_module = require('./recorder');
const recorder = recorder_module.recorder;

const data_change_requires_admin = {
    'user_list': true,
    'itpa_current_device_tracking': true,
    'itpa_current_device_tracking?features': true
};

//data_change_requires_admin[socket_rooms_data_change] = true;
data_change_requires_admin[receive_video_ev] = true;

const redisCreateClientOptions = {
    retry_strategy: function (options) {
        if (options.error && options.error.code === 'ECONNREFUSED') { return new Error('The server refused the connection'); }
        if (options.total_retry_time > 1000 * 60 * 60) { return new Error('Retry time exhausted'); }
        if (options.attempt > 10) { return undefined; }
        return Math.min(options.attempt * 100, 3000);
    },
    password: REDIS_PASSWORD,
    db: REDIS_DB
};

const redisClient = redis.createClient(REDIS_PORT, REDIS_HOST, redisCreateClientOptions);

const redisSub = redis.createClient(REDIS_PORT, REDIS_HOST, redisCreateClientOptions);

redisClient.on('connect', () => { print("redisClient connected"); });

redisClient.on('error', err => { print("redisClient error: " + err.message); });

redisSub.on('connect', () => { print("redisSub connected"); });

redisSub.on('error', err => { print("redisSub error: " + err.message); });

const data_set_change_redis_channel_name = 'data_set_change';

redisSub.on('message', (channel, message) => {
    try {
        if (channel === data_set_change_redis_channel_name) {
            let data_set_name = message;
            getCurrentRoomData(data_set_name, result => {
                io.sockets.to(data_set_name).emit(notify_data_change, data_set_name, result);
            });
        }
    }
    catch (e) {
        print('redisSub exception: ' + e.message);
    }
});

redisSub.subscribe(data_set_change_redis_channel_name);

let videosDirName = 'videos';
let videosTempDirName = videosDirName + '/' + 'video_frames';

let videosDirResolved = path.resolve(videosDirName);

const directory = require('serve-index');
//app.use(directory(your_path));

app.use(cors({
    "credentials": true,
    "origin": true,
    "methods": "GET,HEAD,PUT,PATCH,POST,DELETE",
    "preflightContinue": false,
    "optionsSuccessStatus": 200
}));

app.options('*', cors());

app.use('/videos', directory(videosDirResolved, { icons: true }));
app.use('/videos', express.static(videosDirResolved));

app.use(bodyParser.urlencoded({ limit: '10mb', extended: true }));
app.use(bodyParser.json({ limit: '10mb', extended: true }));

app.get('/', (req, res) => { res.send('Hello, world.\n'); });

app.get('/rooms', (req, res) => { res.send(socket_rooms); });

let last_binary_data;

app.get('/last_frame', (req, res) => {
    res.contentType('image/jpeg');
    let id = req.query.id;
    //print('last_frame: ' + id);
    res.end(socket_rooms_last_frame[req.query.id], 'binary');
});

let all_room_names = {};
let socket_rooms = {};
let socket_rooms_last_frame = {};
let ffmpeg_rtmps = {};

const current_stats = 'current_stats';
app.get('/' + current_stats, (req, res) => {
    let ok = false, result;
    try {
        let timeStampNow = utils.getTimestampNow();
        result = [{
            task_name: 'total_socket_connections',
            count: io.engine.clientsCount,
            completed_on: timeStampNow
        }];
        for (let i in all_room_names) {
            let room_name = i;
            let ioroom = io.sockets.adapter.rooms[room_name];
            let count = ioroom ? ioroom.length : 0
            result.push({
                task_name: room_name + '_connections',
                count: count,
                completed_on: timeStampNow
            });
        }
        ok = true;
    }
    catch (e) { ok = false; print(current_stats + 'exception: ' + e.message); }
    if (ok) { res.json(result); }
    else { res.status(500).send("get current stats failed"); }
});

const delete_video = 'delete_video';
app.post('/' + delete_video, (req, res) => {
    let ok = false;
    try {
        let token = req.body.token;
        let uuid = req.body.uuid;
        //print(delete_video + ' called for ' + uuid + ' with token ' + token);
        if (token === SOCKETIO_TOKEN && uuid && uuid.length) {
            ok = do_delete_video(uuid);
        }
    }
    catch (e) { ok = false; print(delete_video + ' exception: ' + e.message); }
    if (ok) { res.json({ ok: true }); }
    else { res.status(500).send(delete_video + " failed"); }
});

const delete_video_frames = 'delete_video_frames';
app.post('/' + delete_video_frames, (req, res) => {
    let ok = false;
    try {
        let token = req.body.token;
        let uuid = req.body.uuid;
        //print(delete_video_frames + ' called for ' + uuid + ' with token ' + token);
        if (token === SOCKETIO_TOKEN && uuid && uuid.length) {
            ok = do_delete_video_frames(uuid);
        }
    }
    catch (e) { ok = false; print(delete_video_frames + ' exception: ' + e.message); }
    if (ok) { res.json({ ok: true }); }
    else { res.status(500).send(delete_video_frames + " failed"); }
});

const init_itpa_auth = (socket, result) => { if (socket) { socket._itpa_auth = result || {} ; } };

const do_delete_video = uuid => {
    let ok = false;
    try {
        if (uuid && uuid.length) {
            let videoFileName = makeVideoFileName(uuid);
            let thumbFileName = makeThumbFileName(uuid);
            fs.unlinkSync(videoFileName);
            fs.unlinkSync(thumbFileName);
            print(' do_delete_video ' + videoFileName + ' ' + thumbFileName);
            ok = do_delete_video_frames(uuid);
        }
    }
    catch (e) { ok = false; print('do_delete_video exception: ' + e.message); }
    return ok;
};

const do_delete_video_frames = uuid => {
    let ok = false;
    try {
        if (uuid && uuid.length) {
            utils.deleteFolderRecursive(path.resolve(videosTempDirName, uuid));
            ok = true;
        }
    }
    catch (e) { ok = false; print('do_delete_video_frames: ' + e.message); }
    return ok;
};

const socket_authenticate = (socket, data) => {
    return new Promise((resolve, reject) => {
        try {
            if (socket && data) {
                init_itpa_auth(socket);
                let token = data.token;
                if (typeof token === 'string' && token.length > 0) {
                    let url = ITPA_USER_RIGHTS_URL + token;
                    let options = { uri: url, json: true };
                    rp(options).then(result => {
                        result.data = data;
                        delete result.data.token;
                        resolve(result);
                    }).catch(err => reject(err));
                }
                else { reject(new Error('incorrect parameters')); }
            }
            else { reject(new Error('incorrect parameters')); }
        }
        catch (e) { reject(new Error(e.message)); }
    });
};

const socket_track_device = (socket, data) => {
    return new Promise((resolve, reject) => {
        try {
            if (socket && data) {
                if (socket._itpa_is_user) {
                    let url = API_TRACK_DEVICE_URL + utils.makeURLParams(data);
                    let options = { uri: url, json: true };
                    rp(options).then(result => resolve(result)).catch(err => reject(err));
                }
                else { reject(new Error('invalid sender')); }
            }
            else { reject(new Error('incorrect parameters')); }
        }
        catch (e) { reject(new Error(e.message)); }
    });
};

const api_call = (api_url) => {
    return new Promise((resolve, reject) => {
        try {
            let options = { uri: api_url, json: true };
            rp(options).then(result => resolve(result)).catch(err => reject(err));
        }
        catch (e) { reject(new Error(e.message)); }
    });
};

const commonApiVideoCall = (baseURL, socket_data) => {
    //print('commonApiVideoCall: ' + JSON.stringify(socket_data));
    let url = baseURL + utils.makeURLParams(socket_data);
    api_call(url).then(result => {
        if (!result.ok) {
            print('commonApiVideoCall result: (' + url + '): ' + JSON.stringify(result));
        }
    }).catch(err => {
        print('commonApiVideoCall exception (' + url + '): ' + err.message);
    });
};

const addNewApiVideo = (socket_data, uuid, createdTimeMillis) => {
    socket_data.uuid = uuid;
    socket_data.createdOn = utils.getTimestampFromMillis(createdTimeMillis);
    //print('addNewApiVideo: ' + JSON.stringify(socket_data));
    commonApiVideoCall(API_ADD_NEW_BUS_VIDEO_URL, socket_data);
};

const endRecordNewApiVideo = (socket_data, uuid, lastFrameTimeMillis) => {
    socket_data.uuid = uuid;
    socket_data.recordingEnded = utils.getTimestampFromMillis(lastFrameTimeMillis);
    socket_data.processingEnded = utils.getTimestampNow();
    //print('endRecordNewApiVideo: ' + JSON.stringify(socket_data));
    commonApiVideoCall(API_END_RECORD_BUS_VIDEO_URL, socket_data);
};

const checkSocketIsUser = socket => { return socket && socket._itpa_auth && socket._itpa_auth.is_user; };
const checkSocketIsAdmin = socket => { return socket && socket._itpa_auth && socket._itpa_auth.can_admin_itpa; };
//const checkSocketCanSendVideo = socket => { return checkSocketIsAdmin(socket) || (socket && socket._itpa_auth && socket._itpa_auth.can_record_video); };
const checkSocketCanSendVideo = socket => { return socket && socket._can_record_video; };

const checkSocketCanJoinRoom = (socket, roomName) => {
    return socket && roomName && (data_change_requires_admin[roomName]
        ? socket._itpa_auth.can_admin_itpa
        : socket._itpa_auth.is_user === true);
};

const createOrGetRoom = (roomName) => {
    let theRoom = all_room_names[roomName];
    if (theRoom === undefined) {
        theRoom = all_room_names[roomName] = {
            roomName: roomName
        };
    }
    return theRoom;
};

const getCurrentRoomData = (data_set_name, then) => {
    if (data_set_name === socket_rooms_data_change) { then(socket_rooms); }
    else {
        redisClient.get(data_set_name, (err, result) => {
            if (!err) {
                createOrGetRoom(data_set_name);
                try { result = JSON.parse(result); }
                catch (e) { print('getCurrentRoomData exception: ' + e.message); }
                then(result);
            }
        });
    }
};

const emitLastData = (socket, data_set_name) => {
    if (socket) {
        getCurrentRoomData(data_set_name, result => { socket.emit(notify_data_change, data_set_name, result); });
    }
};

const make_video_output_file_name = socket_room => {
    let uuidIndexed = socket_room.room_name + '_' + socket_room.index_count;
    return makeVideoFileName(uuidIndexed);
};

const add_or_get_socket_room = (socket, currentTimeMillis, width, height) => {
    let socket_room;
    try {
        if (socket) {
            let roomKey = socket._room_key;
            cancelDelSocketRoom(roomKey);
            socket_room = socket_rooms[roomKey];
            if (socket_room === undefined) {
                let socket_data = socket._itpa_auth.data;
                let is_persistent = socket._is_persistent;
                let room_name = uuidv4();
                let uuidIndexed = room_name + '_0';
                let folderName = path.resolve(videosTempDirName, uuidIndexed);
                width = width || 640;
                height = height || 480;
                print('add_or_get_socket_room: ' + room_name + ' (' + (is_persistent ? 'persistent' : 'volatile') + ')');
                let now = currentTimeMillis ? currentTimeMillis : Date.now();
                socket_room = socket_rooms[roomKey] = {
                    recog: [],
                    created_time: now,
                    last_index_time: now,
                    last_time: now,
                    index_count: 0,
                    total_frame_count: 0,
                    frame_count: 0,
                    user_name: socket._itpa_auth.user_name,
                    data: socket_data,
                    room_name: room_name,
                    folder_name: folderName,
                    width: width,
                    height: height,
                    is_persistent: is_persistent
                };
                ffmpeg_rtmps[room_name] = utils.ffmpeg_rtmp({ id: room_name });
                broadcast_socket_room_list();
                if (is_persistent) {
                    addNewApiVideo(socket_data, uuidIndexed, now);
                    try {
                        recorder.start_frame_data(socket_room.output_file_name = make_video_output_file_name(socket_room), socket_room.width, socket_room.height);
                    }
                    catch (e) { print('recorder.start_frame_data exception: ' + e.message); }
                    fs.ensureDirSync(folderName);
                }
            }
        }
    } catch (e) { print('add_or_get_socket_room exception: ' + e.message); }
    return socket_room;
};

const get_socket_room = socket => {
    let socket_room;
    try {
        if (socket) {
            let roomKey = socket._room_key;
            socket_room = socket_rooms[roomKey];
            if (socket_room) { cancelDelSocketRoom(roomKey); }
        }
    } catch (e) { socket_room = undefined; print('get_socket_room exception: ' + e.message); }
    return socket_room;
};

const min_frame_count_thumbnail = 30;

const makeFrameFileName = (folderName, index_count, frame_index) => {
    let frame_index_padded = ('' + frame_index).padStart(8, '0');
    let frameBaseFileName = "frame_" + index_count + "_" + frame_index_padded + ".jpg";
    let frameFileName = path.resolve(folderName, frameBaseFileName);
    let lastFrameBaseFileName = "last_frame_" + index_count + ".jpg";
    let lastFrameFileName = path.resolve(folderName, lastFrameBaseFileName);
    return { frameFileName: frameFileName, frameBaseFileName: frameBaseFileName, lastFrameFileName: lastFrameFileName };
};

const makeVideoFileName = uuid => path.resolve(videosDirName, uuid + '.mp4');
const makeThumbFileName = uuid => path.resolve(videosDirName, uuid + '.jpg');

const makeOutputFileName = (uuid, extension) => path.resolve(videosDirName, uuid + extension);

const flush_room = (socket_room, forDelete) => {
    try {
        let old_frame_count = socket_room.frame_count;
        let old_folder_name = socket_room.folder_name;
        let old_index_count = socket_room.index_count;
        let uuidIndexedPrev = socket_room.room_name + '_' + socket_room.index_count;
        socket_room.last_index_time = socket_room.last_time;
        if (socket_room.is_persistent) {
            try {
                let endRecordTime = socket_room.last_index_time;
                recorder.end_frame_data(socket_room.output_file_name, () => {
                    endRecordNewApiVideo(socket_room.data, uuidIndexedPrev, endRecordTime);
                });
            }
            catch (e) {
                print('recorder.end_frame_data exception: ' + e.message);
            }
            if (!forDelete) {
                ++socket_room.index_count;
                let uuidIndexed = socket_room.room_name + '_' + socket_room.index_count;
                let output_file_name = makeVideoFileName(uuidIndexed);
                socket_room.frame_count = 0;
                socket_room.folder_name = path.resolve(videosTempDirName, uuidIndexed);
                addNewApiVideo(socket_room.data, uuidIndexed, socket_room.last_index_time);
                try {
                    recorder.start_frame_data(socket_room.output_file_name = make_video_output_file_name(socket_room), socket_room.width, socket_room.height);
                }
                catch (e) { print('recorder.start_frame_data exception: ' + e.message); }
                fs.ensureDirSync(socket_room.folder_name);
            }
            //else { }
        }
        if (old_frame_count > 0) {
            let thumb_frame_index = min_frame_count_thumbnail;
            if (thumb_frame_index >= old_frame_count) { thumb_frame_index = old_frame_count - 1; }
            let frameFileName = makeFrameFileName(old_folder_name, old_index_count, thumb_frame_index).frameFileName;
            let thumbFileName = makeThumbFileName(uuidIndexedPrev);
            fs.copyFile(frameFileName, thumbFileName, err => {
                if (err) { print('flush_room create thumbnail error: ' + err.message); }
            });

            /*
            let indexBaseFileName = "index_" + old_index_count + ".txt";
            let indexFileName = path.resolve(old_folder_name, indexBaseFileName);
            let videoFileName = makeVideoFileName(uuidIndexedPrev);
            utils.ffmpeg(old_folder_name, indexFileName, videoFileName, () => {
                endRecordNewApiVideo(socket_room.data, uuidIndexedPrev, socket_room.last_time);
            });
            */
        }
    }
    catch (e) { print('flush_room exception: ' + e.message); }
};

const del_socket_room = socket => {
    let roomKey = socket._room_key;
    let room_del = socket_rooms[roomKey];
    if (room_del) {
        let roomName = room_del.room_name;
        delete socket_rooms[roomKey];
        delete socket_rooms_last_frame[roomName];
        if (ffmpeg_rtmps[roomName]) {
            ffmpeg_rtmps[roomName].Kill();
            delete ffmpeg_rtmps[roomName];
        }
        flush_room(room_del, true);
        broadcast_socket_room_list();
        print('del_socket_room: ' + room_del.room_name);
    }
};

const broadcast_socket_room_list = () => {
    io.sockets.to(socket_rooms_data_change).emit(notify_data_change, socket_rooms_data_change, socket_rooms);
};

const video_flush_time = 15 * 60 * 1000;  // every 15 minutes
//const video_flush_time = 1 * 60 * 1000; // every 1 minute

let socketRoomsToDel = {};

const tryDelSocketRoom = socket => {
    let roomKey = socket._room_key;
    if (socketRoomsToDel[roomKey]) {
        print('tryDelSocketRoom deleting: ' + roomKey);
        delete socketRoomsToDel[roomKey];
        try { del_socket_room(socket); }
        catch (e) { print('tryDelSocketRoom exception: ' + e.message); }
    }
};

const cancelDelSocketRoom = roomKey => {
    if (socketRoomsToDel[roomKey]) {
        print('cancelDelSocketRoom deleting: ' + roomKey);
        clearTimeout(socketRoomsToDel[roomKey]);
        delete socketRoomsToDel[roomKey];
    }
};

const socket_room_del_timeout_millis = 30 * 1000;

const addDelSocketRoom = socket => {
    let roomKey = socket._room_key;
    if (socket_rooms[roomKey]) {
        print('addDelSocketRoom: ' + roomKey);
        socketRoomsToDel[roomKey] = setTimeout(() => { tryDelSocketRoom(socket); }, socket_room_del_timeout_millis);
    }
};

io.sockets.on(connection_ev, (socket) => {
    const _id = socket.id;
    init_itpa_auth(socket);
    print(connection_ev + ': ' + _id);
    //socket.emit(connected_ev, _id);

    socket.on(join_socket_room_ev, (data) => {
        try {
            if (data && data.room_name && typeof data.room_name === 'string' && data.room_name.length > 0) {
                print('joined socket room ' + data.room_name);
                socket.join(data.room_name);
            }
        }
        catch (e) { print(join_socket_room_ev + ' exception: ' + e); }
    });
    socket.on(leave_socket_room_ev, (data) => {
        try {
            if (data && data.room_name && typeof data.room_name === 'string' && data.room_name.length > 0) {
                print('left socket room ' + data.room_name);
                socket.leave(data.room_name);
            }
        }
        catch (e) { print(leave_socket_room_ev + ' exception: ' + e); }
    });

    socket.on(disconnect_ev, () => {
        try {
            //del_socket_room(_id);
            addDelSocketRoom(socket);
        }
        catch (e) {
            print('socket disconnect exception: ' + e.message);
        }
        print(disconnect_ev + ': ' + _id);
    });
    socket.on(track_device_ev, (data) => {
        //print(track_device_ev + ' ' + _id + ' ' + JSON.stringify(data));
        socket_track_device(
            socket, data
        ).then(result => {
            //print(track_device_ev + ' ' + _id + ' ' + JSON.stringify(result));
            socket.emit(track_device_ev, result);
        }).catch(err => {
            //print(track_device_ev + ' ' + _id + ' exception: ' + err.message);
            socket.emit(track_device_ev, { exception: err.message });
        });
    });
    socket.on(authentication_ev, (data) => {
        //print(authentication_ev + ' ' + _id);
        socket_authenticate(
            socket, data
        ).then(result => {
            print(authentication_ev + ' ' + _id + ' ' + JSON.stringify(result));
            if (result) {
                init_itpa_auth(socket, result);
                let itpa_auth = socket._itpa_auth;
                let socket_data = itpa_auth ? socket._itpa_auth.data : undefined;
                socket._itpa_is_user = itpa_auth && itpa_auth.is_user;
                socket._can_record_video = itpa_auth && (itpa_auth.can_record_video || itpa_auth.can_admin_itpa);
                socket._is_persistent = (socket_data && socket_data.bus_fleet && socket_data.bus_id && socket_data.bus_name);
                if (socket._is_persistent) {
                    socket._room_key = socket_data.bus_fleet + '|' + socket_data.bus_id + '|' + socket_data.camera_type;
                    print(authentication_ev + ' socket is persistent, key ' + socket._room_key);
                }
                else { print(authentication_ev + ' socket is not persistent'); }
            }
            socket.emit(authenticated_ev, result);
        }).catch(err => {
            socket.emit(authenticated_ev, { exception: err.message });
        });
    });
    socket.on(get_last_data_set, function (data_set_name) {
        try {
            if (typeof data_set_name === 'string' && data_set_name.length > 0) {
                //print(get_last_data_set + ': ' + data_set_name);
                if (checkSocketCanJoinRoom(socket, data_set_name)) {
                    emitLastData(socket, data_set_name);
                }
                //else { print(get_last_data_set + ' failed for ' + data_set_name); }
            }
        }
        catch (e) { print(get_last_data_set + ' exception: ' + e); }
    });
    socket.on(subscribe_data_change, (data_set_name, preventEmitBack) => {
        try {
            if (typeof data_set_name === 'string' && data_set_name.length > 0) {
                //print(subscribe_data_change + ': ' + data_set_name);
                if (checkSocketCanJoinRoom(socket, data_set_name)) {
                    if (!preventEmitBack) { emitLastData(socket, data_set_name); }
                    socket.join(data_set_name);
                }
                //else { print(subscribe_data_change + ' failed for ' + data_set_name); }
            }
        }
        catch (e) { print(subscribe_data_change + ' exception: ' + e); }
    });
    socket.on(unsubscribe_data_change, (data_set_name) => {
        try {
            if (typeof data_set_name === 'string' && data_set_name.length > 0) {
                //print(unsubscribe_data_change + ': ' + data_set_name);
                socket.leave(data_set_name);
            }
        }
        catch (e) { print(unsubscribe_data_change + ' exception: ' + e); }
    });
    socket.on(send_status_ev, (data) => {
        try {
            if (checkSocketCanSendVideo(socket)) {
                let socket_room = get_socket_room(socket);
                if (socket_room) {
                    socket_room.room_status = data;
                    //print(send_status_ev + ': ' + JSON.stringify(data));
                    broadcast_socket_room_list();
                }
            }
        }
        catch (e) { print(send_status_ev + ' exception: ' + e.message); }
    });
    socket.on(send_video_ev, (data) => {
        try {
            if (checkSocketCanSendVideo(socket)) {
                let socket_room = add_or_get_socket_room(socket, data.currentTimeMillis, data.width, data.height);
                if (socket_room) {

                    data.recog = socket_room.recog;

                    //io.sockets.to(socket_room.room_name).volatile.emit(receive_video_ev, socket_room, data);
                    io.sockets.to(socket_room.room_name).compress(false).binary(true).volatile.emit(receive_video_ev, socket_room, data);

                    if (socket_room.is_persistent) {
                        let binaryData = data.data;
                        let hasTime = data.currentTimeMillis !== undefined;
                        let now = hasTime ? data.currentTimeMillis : Date.now();
                        let durationMillis = now - socket_room.last_time;

                        if (durationMillis > 0 || (now === socket_room.last_time)) {

                            let durationSecs = durationMillis / 1000;

                            //if (!hasTime) { console.log('using server time'); }

                            socket_room.last_time = now;

                            if (now - socket_room.last_index_time >= video_flush_time) { flush_room(socket_room, false); }

                            let millisInVideo = now - socket_room.last_index_time;

                            let frameFileNames = makeFrameFileName(socket_room.folder_name, socket_room.index_count, socket_room.frame_count);

                            ++socket_room.frame_count;
                            ++socket_room.total_frame_count;

                            try { recorder.set_frame_data(socket_room.output_file_name, binaryData, millisInVideo); }
                            catch (e) { print('recorder.set_frame_data exception: ' + e.message); }

                            fs.writeFile(frameFileNames.frameFileName, binaryData, 'binary', function (err) {
                                if (err) { print(err); }
                            });

                            socket_rooms_last_frame[socket_room.room_name] = binaryData;

                            let indexBaseFileName = "index_" + socket_room.index_count + ".txt";
                            let indexFileName = path.resolve(socket_room.folder_name, indexBaseFileName);

                            if (socket_room.frame_count > 1) {
                                let strDuration = "duration " + durationSecs + "\n";
                                fs.appendFileSync(indexFileName, strDuration);
                            }
                            fs.appendFileSync(indexFileName, "file '" + frameFileNames.frameBaseFileName + "'\n");

                            if ((socket_room.total_frame_count % 16) === 0) {
                            //if (!socket_room.isCalculatingCV) {
                                socket_room.isCalculatingCV = true;
                                let analysisResult = { recog: [] };
                                cv.imdecodeAsync(
                                    binaryData
                                ).then(img => {
                                    analysisResult.img = img;
                                    return img.bgrToGrayAsync();
                                }).then(grayImg => {
                                    analysisResult.grayImg = grayImg;
                                    return frontalFaceAlt2Classifier.detectMultiScaleAsync(grayImg);
                                }).then((res) => {
                                    const { objects, numDetections } = res;
                                    objects.forEach((rect, i) => {
                                        analysisResult.recog.push({ x: rect.x, y: rect.y, w: rect.width, h: rect.height, numDetections: numDetections[i], isFrontalFace: true });
                                    });
                                    return profileFaceClassifier.detectMultiScaleAsync(analysisResult.grayImg);
                                }).then(res => {
                                    const { objects, numDetections } = res;
                                    objects.forEach((rect, i) => {
                                        analysisResult.recog.push({ x: rect.x, y: rect.y, w: rect.width, h: rect.height, numDetections: numDetections[i], isProfileFace: true });
                                    });
                                }).then(() => {
                                    socket_room.recog = analysisResult.recog;
                                    socket_room.isCalculatingCV = false;
                                }).catch(err => {
                                    console.error(err);
                                    socket_room.isCalculatingCV = false;
                                });

                                /*recorder.analyse_frame(binaryData, (result) => {
                                    socket_room.recog = result;
                                    socket_room.isCalculatingCV = false;
                                });*/
                            }
                        }
                        else { print('frame out of sequence: ' + _id); }
                    }
                }
            }
            //else { print(send_video_ev + ' cant record ' + _id); }
        }
        catch (e) { print(send_video_ev + ' exception: ' + e.message); }
    });
    socket.on(end_send_ev, () => {
        try {
            if (checkSocketCanSendVideo(socket)) {
                let socket_room = get_socket_room(socket);
                if (socket_room) {
                    print(end_send_ev + ' received, deleting room');
                    del_socket_room(socket);
                }
            }
        }
        catch (e) { print(end_send_ev + ' exception: ' + e.message); }
    });
});

server.listen(SOCKETIO_PORT, SOCKETIO_HOST);

print(`Running on http://${SOCKETIO_HOST}:${SOCKETIO_PORT}`);

recorder_module.test();

process.on('uncaughtException', function (err) {
    console.log('*** UNCAUGHT (caught on process) ERROR ' + err);
});


/*
/opencv4nodejs/node_modules/opencv4nodejs/lib/haarcascades
-rw-r--r--    1 root     root        353619 Apr 23 12:41 haarcascade_eye.xml
-rw-r--r--    1 root     root        624280 Apr 23 12:41 haarcascade_eye_tree_eyeglasses.xml
-rw-r--r--    1 root     root        425918 Apr 23 12:41 haarcascade_frontalcatface.xml
-rw-r--r--    1 root     root        396460 Apr 23 12:41 haarcascade_frontalcatface_extended.xml
-rw-r--r--    1 root     root        701059 Apr 23 12:41 haarcascade_frontalface_alt.xml
-rw-r--r--    1 root     root        561335 Apr 23 12:41 haarcascade_frontalface_alt2.xml
-rw-r--r--    1 root     root       2785524 Apr 23 12:41 haarcascade_frontalface_alt_tree.xml
-rw-r--r--    1 root     root        963441 Apr 23 12:41 haarcascade_frontalface_default.xml
-rw-r--r--    1 root     root        493855 Apr 23 12:41 haarcascade_fullbody.xml
-rw-r--r--    1 root     root        202759 Apr 23 12:41 haarcascade_lefteye_2splits.xml
-rw-r--r--    1 root     root         47775 Apr 23 12:41 haarcascade_licence_plate_rus_16stages.xml
-rw-r--r--    1 root     root        409376 Apr 23 12:41 haarcascade_lowerbody.xml
-rw-r--r--    1 root     root        858204 Apr 23 12:41 haarcascade_profileface.xml
-rw-r--r--    1 root     root        203577 Apr 23 12:41 haarcascade_righteye_2splits.xml
-rw-r--r--    1 root     root         78138 Apr 23 12:41 haarcascade_russian_plate_number.xml
-rw-r--r--    1 root     root        195379 Apr 23 12:41 haarcascade_smile.xml
-rw-r--r--    1 root     root        813951 Apr 23 12:41 haarcascade_upperbody.xml
*/