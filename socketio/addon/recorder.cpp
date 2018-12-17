#include "utils.h"

/*

ffmpeg -loop 1 -i t.jpg -c:v libx264 -preset veryfast -r 25 -maxrate 3000k -bufsize 6000k -pix_fmt yuv420p -g 50 -f flv rtmp://video:1935/live/test

ffmpeg -re -loop 1 -f image2 -i t.jpg -c:v libx264 -preset veryfast -r 25 -maxrate 3000k -bufsize 6000k -pix_fmt yuv420p -g 50 -f flv rtmp://video:1935/live/test

ffmpeg -re -loop 1 -f image2 -i t.jpg -c:v libx264 -tune zerolatency -profile:v baseline -preset superfast -r 25 -maxrate 3000k -bufsize 6000k -pix_fmt yuv420p -g 50 -f flv rtmp://video:1935/live/test


ffmpeg -re -loop 1 -f image2 -i t.jpg -c:v libx264 -tune zerolatency -preset veryfast -r 25 -maxrate 3000k -bufsize 6000k -pix_fmt yuv420p -g 25 -f flv rtmp://video:1935/live/test

ffmpeg -re -loop 1 -f image2 -i last_frame_0.jpg -c:v libx264 -tune zerolatency -preset veryfast -r 25 -maxrate 3000k -bufsize 6000k -pix_fmt yuv420p -g 25 -f flv rtmp://video:1935/live/test

ffmpeg -re -loop 1 -f image2 -i last_frame_0.jpg -c:v libx264 -tune zerolatency -preset veryfast -r 25 -maxrate 3000k -bufsize 6000k -pix_fmt yuv420p -g 25 -f flv rtmp://video:1935/live/test

ffmpeg -re -loop 1 -f image2 -i http://localhost:1337/last_frame?id=_DNMUnQ7LYlZ6AaAAAAB -c:v libx264 -tune zerolatency -preset veryfast -r 25 -maxrate 3000k -bufsize 6000k -pix_fmt yuv420p -g 25 -f flv rtmp://video:1935/live/test




ffmpeg -re -loop 1 -f image2 -i http://localhost:1337/last -c:v libx264 -profile:v baseline -maxrate 400k -bufsize 1835k -pix_fmt yuv420p -flags -global_header -hls_time 10 -hls_list_size 6 -hls_wrap 10 -start_number 1 test.m3u8

ffmpeg -re -loop 1 -f image2 -i http://localhost:1337/last -c:v libx264 -preset superfast -profile:v baseline -maxrate 3000k -bufsize 6000k -pix_fmt yuv420p -flags -global_header -hls_time 5 -hls_list_size 0 -hls_wrap 5 -start_number 1 test.m3u8

ffmpeg -re -loop 1 -f image2 -i http://localhost:1337/last -c:v libx264 -preset superfast -profile:v baseline -maxrate 3000k -bufsize 6000k -pix_fmt yuv420p -flags -global_header -hls_time 5 -hls_list_size 0 -hls_wrap 5 -start_number 1 test.m3u8

ffmpeg -y \
-loop 1 -f image2 -i http://localhost:1337/last \
-codec copy \
-map 0 \
-f segment \
-segment_time 10 \
-segment_format mpegts \
-segment_list "./test.m3u8" \
-segment_list_type m3u8 \
"./test%d.ts"


http://localhost/oc/playvideo.html?src=http://192.168.0.37:8080/videos-http/hls/test.m3u8

http://localhost/oc/playvideo.html?src=http://192.168.0.37:8080/videos-http/hls/last.m3u8




*/

Napi::String Hello(const Napi::CallbackInfo& info) {
	Napi::Env env = info.Env();
	return Napi::String::New(env, "world");
};

dyn_recorders recorders;

Napi::Value StartFrameData(const Napi::CallbackInfo& info) {
	string result = "ok";
	Napi::Env env = info.Env();
	try {
		struct data { string outputFileName; uint32_t width, height; };
		Napi::Function callback = info[0].As<Napi::Function>();
		data *localData = new data;
		localData->outputFileName = info[1].As<Napi::String>().Utf8Value();
		localData->width = info[2].As<Napi::Number>().Uint32Value();;
		localData->height = info[3].As<Napi::Number>().Uint32Value();
		std::cerr << "StartFrameData " << localData->outputFileName << " " << to_string(localData->width) << " " << to_string(localData->height) << std::endl;
		std::function<void(NapiAsyncWorker *pAsyncWorker)> onExecute = [](NapiAsyncWorker *pAsyncWorker)->void {
			data *asyncData = (data *)pAsyncWorker->GetData();
			recorders.addRecorder(asyncData->outputFileName, asyncData->width, asyncData->height, 30);
		};
		std::function<void(NapiAsyncWorker *pAsyncWorker)> onOK = [](NapiAsyncWorker *pAsyncWorker)->void {
			Napi::Env env = pAsyncWorker->Env();
			data *asyncData = (data *)pAsyncWorker->GetData();
			pAsyncWorker->Callback().Call({ Napi::String::New(env, asyncData->outputFileName) });
			delete asyncData;
		};
		NapiAsyncWorker *napiAsyncWorker = new NapiAsyncWorker(callback, onExecute, onOK, (void *)localData);
		napiAsyncWorker->Queue();
	}
	catch (std::exception e) { result = e.what(); std::cerr << "StartFrameData exception: " << e.what() << std::endl; }
	return Napi::String::New(env, result);
};

Napi::Value SetFrameData(const Napi::CallbackInfo& info) {
	string result = "ok";
	Napi::Env env = info.Env();
	try {
		struct data { 
			string outputFileName; 
			FrameInfo *frameInfo;
			data() { frameInfo = NULL; }
			~data() { 
				if (frameInfo) { 
					//delete frameInfo; 
					frameInfo = NULL;
					//std::cerr << "SetFrameData data deleted frame info" << std::endl;
				}
			}
		};
		data *localData = new data;
		Napi::Function callback = info[0].As<Napi::Function>();
		localData->outputFileName = info[1].As<Napi::String>().Utf8Value();

		size_t bufferLen;
		void *buffer;

		napi_get_buffer_info(env, info[2], & buffer, &bufferLen);

		OffsetMillis positionMillis = (OffsetMillis)info[3].As<Napi::Number>().Int64Value();;

		localData->frameInfo = new FrameInfo(buffer, bufferLen, positionMillis);

		//std::cerr << "SetFrameData " << localData->outputFileName << " len: " << std::to_string(bufferLen) << " millis: " << std::to_string(positionMillis) << std::endl;

		std::function<void(NapiAsyncWorker *pAsyncWorker)> onExecute = [](NapiAsyncWorker *pAsyncWorker)->void {
			data *asyncData = (data *)pAsyncWorker->GetData();
			auto rec = recorders.getRecorder(asyncData->outputFileName);
			if (rec) { rec->addFrame(asyncData->frameInfo); }
		};
		std::function<void(NapiAsyncWorker *pAsyncWorker)> onOK = [](NapiAsyncWorker *pAsyncWorker)->void {
			Napi::Env env = pAsyncWorker->Env();
			data *asyncData = (data *)pAsyncWorker->GetData();
			pAsyncWorker->Callback().Call({ Napi::String::New(env, asyncData->outputFileName) });
			delete asyncData;
		};

		NapiAsyncWorker *napiAsyncWorker = new NapiAsyncWorker(callback, onExecute, onOK, (void *)localData);
		napiAsyncWorker->Queue();
	}
	catch (std::exception e) { result = e.what(); std::cerr << "SetFrameData exception: " << e.what() << std::endl; }
	return Napi::String::New(env, result);
};


Napi::Value EndFrameData(const Napi::CallbackInfo& info) {
	string result = "ok";
	Napi::Env env = info.Env();
	try {
		struct data { string outputFileName; };
		Napi::Function callback = info[0].As<Napi::Function>();
		data *localData = new data;
		localData->outputFileName = info[1].As<Napi::String>().Utf8Value();
		std::cerr << "EndFrameData " << localData->outputFileName << std::endl;
		std::function<void(NapiAsyncWorker *pAsyncWorker)> onExecute = [](NapiAsyncWorker *pAsyncWorker)->void {
			data *asyncData = (data *)pAsyncWorker->GetData();
			recorders.delRecorder(asyncData->outputFileName);
		};
		std::function<void(NapiAsyncWorker *pAsyncWorker)> onOK = [](NapiAsyncWorker *pAsyncWorker)->void {
			Napi::Env env = pAsyncWorker->Env();
			data *asyncData = (data *)pAsyncWorker->GetData();
			pAsyncWorker->Callback().Call({ Napi::String::New(env, asyncData->outputFileName) });
			delete asyncData;
		};
		NapiAsyncWorker *napiAsyncWorker = new NapiAsyncWorker(callback, onExecute, onOK, (void *)localData);
		napiAsyncWorker->Queue();
	}
	catch (std::exception e) { result = e.what(); std::cerr << "EndFrameData exception: " << e.what() << std::endl; }
	return Napi::String::New(env, result);
};

CascadeClassifier faceCascade, eyesCascade;

void InitOpenCV() {
	try {
		eyesCascade.load("/usr/local/share/OpenCV/haarcascades/haarcascade_eye_tree_eyeglasses.xml");
		//faceCascade.load("/usr/local/share/OpenCV/haarcascades/haarcascade_frontalface_alt2.xml");
		//faceCascade.load("/usr/local/share/OpenCV/haarcascades/haarcascade_frontalface_alt.xml");
		faceCascade.load("/usr/local/share/OpenCV/haarcascades/haarcascade_frontalface_default.xml");
		//faceCascade.load("/usr/local/share/OpenCV/haarcascades/haarcascade_upperbody.xml");
		//faceCascade.load("/usr/src/app/cascadeH5.xml");
		
		//faceCascade.load("/usr/local/share/OpenCV/lbpcascades/lbpcascade_frontalcatface.xml");

		//faceCascade.load("/usr/local/share/OpenCV/haarcascades/haarcascade_frontalcatface_extended.xml");

		cerr << "faceCascade is " << (faceCascade.empty() ? "failed" : "open") << endl;
		cerr << "eyesCascade is " << (eyesCascade.empty() ? "failed" : "open") << endl;
	}
	catch (std::exception e) { 
		std::cerr << "InitOpenCV exception: " << e.what() << std::endl; 
	}
};

class DetectResult {
public:
	Rect face;
	vector<Rect>eyes;
};

class DetectResults {
public:
	vector<DetectResult>results;
};

DetectResults detectFacesAndEyes(Mat& img) {
	DetectResults drs;
	Mat gray;
	vector<Rect> faces;

	cvtColor(img, gray, COLOR_BGR2GRAY);
	equalizeHist(gray, gray);
	faceCascade.detectMultiScale(gray, faces, 1.1, 5);

	size_t nFaces = faces.size();

	if (nFaces > 0) {
		cerr << "Found: " << nFaces << " faces" << endl;
		for (size_t i = 0; i < nFaces; i++) {
			Rect r = faces[i];
			DetectResult dr;
			dr.face = r;
			Mat faceROI = gray(r);
			eyesCascade.detectMultiScale(faceROI, dr.eyes);
			drs.results.push_back(dr);
		}
	}

	return drs;
};

Napi::Value AnalyseFrame(const Napi::CallbackInfo& info) {
	string result = "ok";
	Napi::Env env = info.Env();
	try {
		struct data {
			DetectResults drs;
			FrameInfo *frameInfo;
			data() { frameInfo = NULL; }
			~data() {
				if (frameInfo) {
					delete frameInfo; 
					frameInfo = NULL;
					//std::cerr << "AnalyseFrame data deleted frame info" << std::endl;
				}
			}
		};
		data *localData = new data;
		Napi::Function callback = info[0].As<Napi::Function>();

		size_t bufferLen;
		void *buffer;

		napi_get_buffer_info(env, info[1], &buffer, &bufferLen);

		localData->frameInfo = new FrameInfo(buffer, bufferLen, 0);

		//std::cerr << "AnalyseFrame " << localData->outputFileName << " len: " << std::to_string(bufferLen) << " millis: " << std::to_string(positionMillis) << std::endl;

		std::function<void(NapiAsyncWorker *pAsyncWorker)> onExecute = [](NapiAsyncWorker *pAsyncWorker)->void {
			data *asyncData = (data *)pAsyncWorker->GetData();
			FrameInfo *fi = asyncData->frameInfo;
			Mat rawData(1, fi->bufferLen, CV_8UC1, fi->buffer);
			Mat decodedImage = imdecode(rawData, CV_LOAD_IMAGE_COLOR);
			asyncData->drs = detectFacesAndEyes(decodedImage);
		};

		std::function<void(NapiAsyncWorker *pAsyncWorker)> onOK = [](NapiAsyncWorker *pAsyncWorker)->void {
			Napi::Env env = pAsyncWorker->Env();
			data *asyncData = (data *)pAsyncWorker->GetData();
			DetectResults *drs = &asyncData->drs;
			napi_value arr, obj, xValue, yValue, wValue, hValue;
			napi_create_array(env, &arr);

			for (size_t i = 0; i < drs->results.size(); ++i) {
				napi_create_object(env, &obj);
				//string str = std::to_string(i) + " hello";
				Rect *face = &drs->results[i].face;
				napi_create_double(env, face->x, &xValue);
				napi_create_double(env, face->y, &yValue);
				napi_create_double(env, face->width, &wValue);
				napi_create_double(env, face->height, &hValue);
				//cerr << "Found: x: " << dr->faces[i].x << " y " << dr->faces[i].y << endl;
				napi_set_named_property(env, obj, "x", xValue);
				napi_set_named_property(env, obj, "y", yValue);
				napi_set_named_property(env, obj, "w", wValue);
				napi_set_named_property(env, obj, "h", hValue);
				napi_set_element(env, arr, i, obj);
			}

			pAsyncWorker->Callback().Call({ arr });
			delete asyncData;
		};

		NapiAsyncWorker *napiAsyncWorker = new NapiAsyncWorker(callback, onExecute, onOK, (void *)localData);
		napiAsyncWorker->Queue();
	}
	catch (std::exception e) { result = e.what(); std::cerr << "AnalyseFrame exception: " << e.what() << std::endl; }
	return Napi::String::New(env, result);
};

Napi::Object Init(Napi::Env env, Napi::Object exports) {
	FFmpegInitialize();
	InitOpenCV();
	exports.Set(Napi::String::New(env, "start_frame_data"), Napi::Function::New(env, StartFrameData));
	exports.Set(Napi::String::New(env, "set_frame_data"), Napi::Function::New(env, SetFrameData));
	exports.Set(Napi::String::New(env, "end_frame_data"), Napi::Function::New(env, EndFrameData));
	exports.Set(Napi::String::New(env, "analyse_frame"), Napi::Function::New(env, AnalyseFrame));
	exports.Set(Napi::String::New(env, "hello"), Napi::Function::New(env, Hello));
	return exports;
};

NODE_API_MODULE(NODE_GYP_MODULE_NAME, Init)
