#pragma once

#pragma GCC diagnostic ignored "-Wdeprecated-declarations"

#include <stdio.h>
#include <iostream>
#include <bitset>
#include <numeric>
#include <iostream>
#include <fstream>
#include <functional>
#include <iomanip>
#include <list>
#include <map>
#include <set>
#include <mutex>
#include <unordered_set>
#include <unordered_map>
#include <stack>
#include <math.h>
#include <algorithm>
#include <queue>
#include <sstream>
#include <string.h>
#include <string>
#include <vector>
#include <chrono>
#include <regex>
#include <stdint.h>
#include <thread>
#include <atomic>

#include <unistd.h>
#include <assert.h>
//#include <node.h>
//#include <node_api.h>
#include <napi.h>
//#include <node_api_types.h>

extern "C" {
#include <x264.h>
#include <libswscale/swscale.h>
#include <libavcodec/avcodec.h>
#include <libavutil/mathematics.h>
#include <libavformat/avformat.h>
#include <libavutil/opt.h>
}

#include <opencv2/opencv.hpp>
#include <opencv2/imgcodecs.hpp>
#include <opencv2/core/core.hpp>
#include <opencv2/highgui/highgui.hpp>
#include <opencv2/objdetect.hpp>
#include <opencv2/imgproc.hpp>

using namespace std::chrono;
using namespace std;

using namespace cv;

using OffsetMillis = int64_t;
using BufferLen = size_t;

extern std::string b64decode(const void* data, const size_t len);
extern std::vector<uchar> cv_mat_to_vector(cv::Mat mat);

extern void FFmpegInitialize(void);

extern void rgbFrameFromJpegMat(AVFrame &toFrame, cv::Mat &fromMat, unsigned int width, unsigned int height);

class FrameInfo {
public:
	void * buffer;
	BufferLen bufferLen;
	OffsetMillis frame_position_millis;
	FrameInfo(void * buffer, BufferLen bufferLen, OffsetMillis frame_position_millis) :
		bufferLen(bufferLen), frame_position_millis(frame_position_millis) {
		size_t bufferSize = (size_t)bufferLen * sizeof(unsigned char);
		this->buffer = (void*)malloc(bufferSize);
		memmove(this->buffer, buffer, bufferSize);
	};
	~FrameInfo() {
		try { if (buffer) { free(buffer); buffer = NULL; } }
		catch (std::exception e) { std::cerr << "FrameInfo destructor exception " << e.what() << std::endl; }
	}
};

extern void ffmpegThreadRecord(
	std::mutex & curFrameAccess,
	std::atomic<bool> & workdone,
	std::queue <FrameInfo*>&frameInfos,
	int fps,
	unsigned int width,
	unsigned int height,
	SwsContext* swsCtx,
	AVFrame *rgbpic,
	AVFrame *yuvpic,
	bool needsClose,
	AVStream* pStream,
	AVFormatContext* pFormatContext
);

class FFMpegThreadRecorder {
private:
	bool is_open, is_released;
	unsigned int width, height;
	int fps, millisPerFrame;
	AVRational fpsR;
	SwsContext* swsCtx;
	AVOutputFormat* pOutputFormat;
	AVStream* pStream;
	AVFormatContext* pFormatContext;
	AVPacket pkt;
	AVFrame *rgbpic, *yuvpic;

	std::mutex curFrameAccess;
	std::atomic<bool> workdone;
	std::thread recordThread;

	queue <FrameInfo*> frameInfos;

	void emptyFrameInfos() {
		while (!frameInfos.empty()) {
			FrameInfo *fi = frameInfos.front();
			frameInfos.pop();
			delete fi;
		}
	};

	void release() {
		if (is_open) {
			is_open = false;
			is_released = true;
			workdone = true;
			recordThread.join();
			try { emptyFrameInfos(); }
			catch (std::exception e) { is_open = false; std::cerr << "FFMpegThreadRecorder: release emptyFrameInfos" << e.what() << std::endl; }
		}
	};

public:
	FFMpegThreadRecorder() { is_released = is_open = false; workdone = false; };
	virtual ~FFMpegThreadRecorder() {
		try { release(); }
		catch (std::exception e) { std::cerr << "FFMpegThreadRecorder destructor exception: " << e.what() << std::endl; }
	};

	void init(const string filenameParam, unsigned int _width, unsigned int _height, int _fps) {
		if (!is_released && !is_open) {
			try {
				fps = _fps;
				width = _width;
				height = _height;

				millisPerFrame = 1000 / fps;

				fpsR = (AVRational) { 1, fps };

				swsCtx = sws_getContext(width, height, AV_PIX_FMT_RGB24, width, height, AV_PIX_FMT_YUV420P, SWS_FAST_BILINEAR, NULL, NULL, NULL);
				//const char* fmtext = "mp4";
				pOutputFormat = av_guess_format(NULL, NULL, "video/mp4");

				//string filename = "rtmp://video:1935/live/" + filenameParam;
				string filename = filenameParam;
				const char *pFileName = filename.c_str();

				avformat_alloc_output_context2(&pFormatContext, pOutputFormat, NULL, pFileName);

				AVCodec* codec = avcodec_find_encoder_by_name("libx264");
				AVDictionary* opt = NULL;
				av_dict_set(&opt, "preset", "slow", 0);
				av_dict_set(&opt, "crf", "25", 0); //-s 1280x720
				av_dict_set(&opt, "s", "1280x720", 0);
				pStream = avformat_new_stream(pFormatContext, codec);
				AVCodecContext* pCodec = pStream->codec;
				pCodec->width = width;
				pCodec->height = height;
				pCodec->pix_fmt = AV_PIX_FMT_YUV420P;
				pCodec->time_base = fpsR;

				if (pFormatContext->oformat->flags & AVFMT_GLOBALHEADER) { pCodec->flags |= AV_CODEC_FLAG_GLOBAL_HEADER; }
				avcodec_open2(pCodec, codec, &opt);
				av_dict_free(&opt);

				pStream->time_base = fpsR;
				av_dump_format(pFormatContext, 0, pFileName, 1);
				avio_open(&pFormatContext->pb, pFileName, AVIO_FLAG_WRITE);
				int ret = avformat_write_header(pFormatContext, &opt);
				av_dict_free(&opt);

				if (ret < 0) {
					is_open = false;
					cerr << "FFMpegThreadRecorder: open video avformat_write_header failed " << std::endl;
				}
				else {
					rgbpic = av_frame_alloc();
					rgbpic->format = AV_PIX_FMT_RGB24;
					rgbpic->width = width;
					rgbpic->height = height;
					av_frame_get_buffer(rgbpic, 1);

					yuvpic = av_frame_alloc();
					yuvpic->format = AV_PIX_FMT_YUV420P;
					yuvpic->width = width;
					yuvpic->height = height;
					av_frame_get_buffer(yuvpic, 1);

					is_open = true;

					bool needsClose = !(pOutputFormat->flags & AVFMT_NOFILE);

					recordThread = std::thread(
						ffmpegThreadRecord,
						std::ref(curFrameAccess),
						std::ref(workdone),
						std::ref(frameInfos),
						fps, width, height,
						swsCtx, rgbpic, yuvpic, needsClose, pStream, pFormatContext);
				}
			}
			catch (std::exception e) { is_open = false; std::cerr << "FFMpegThreadRecorder: open video exception " << e.what() << std::endl; }
		}
	};

	bool addFrame(FrameInfo *newFrameInfo) {
		bool result = false;
		if (is_open) {
			try {
				std::unique_lock<std::mutex> lk(curFrameAccess);
				frameInfos.push(newFrameInfo);
				result = true;
			}
			catch (std::exception e) { std::cerr << "FFMpegThreadRecorder: add frame" << e.what() << std::endl; }
		}
		else { std::cerr << "FFMpegThreadRecorder: add frame NOT OPEN" << std::endl; }
		return result;
	};
};

class dyn_recorder {
	string output_file_name;
	FFMpegThreadRecorder * m_recorder;
	void release() { if (m_recorder) { delete m_recorder; m_recorder = NULL; } };
public:

	dyn_recorder(string & output_file_name, unsigned int width, unsigned int height, int fps) : output_file_name(output_file_name) {
		m_recorder = new FFMpegThreadRecorder();
		m_recorder->init(output_file_name, width, height, fps);
	};
	~dyn_recorder() {
		try { release(); }
		catch (std::exception e) { std::cerr << "dyn_recorder destructor exception: " << e.what() << std::endl; }
	};
	bool addFrame(FrameInfo *newFrameInfo) { return m_recorder->addFrame(newFrameInfo); };
};

class dyn_recorders {
	unordered_map<string, dyn_recorder*> recorders;
	void release() {
		for (auto it = recorders.begin(); it != recorders.end(); ) {
			delete it->second;
			it = recorders.erase(it);
		}
	};
public:
	~dyn_recorders() {
		try { release(); }
		catch (std::exception e) { std::cerr << "dyn_recorders destructor exception: " << e.what() << std::endl; }
	}

	void addRecorder(string & output_file_name, unsigned int width, unsigned int height, int fps) {
		recorders[output_file_name] = new dyn_recorder(output_file_name, width, height, fps);
	};

	dyn_recorder * getRecorder(string & output_file_name) {
		auto recorderit = recorders.find(output_file_name);
		return recorderit != recorders.end() ? recorderit->second : NULL;
	};

	void delRecorder(string & output_file_name) {
		auto recorderit = recorders.find(output_file_name);
		if (recorderit != recorders.end()) {
			delete recorderit->second;
			recorders.erase(recorderit);
		}
	};
};

class NapiAsyncWorker;

using NapiAsyncWorkerCB = std::function<void(NapiAsyncWorker *pAsyncWorker)>;

class NapiAsyncWorker : public Napi::AsyncWorker {
	NapiAsyncWorkerCB onExecute, onOK;
	void *data;
public:
	NapiAsyncWorker(
		Napi::Function& callback, NapiAsyncWorkerCB &onExecute, NapiAsyncWorkerCB &onOK, void *data)
		: Napi::AsyncWorker(callback), onExecute(onExecute), onOK(onOK), data(data) {
		//std::cerr << "NapiAsyncWorker constructor" << std::endl;
	};
	~NapiAsyncWorker() {
		//std::cerr << "NapiAsyncWorker destructor" << std::endl;
	};

	void * GetData() { return data; };

	void Execute() {
		//std::cerr << "NapiAsyncWorker execute start" << std::endl;
		try { onExecute(this); }
		catch (std::exception e) { std::cerr << "NapiAsyncWorker Execute exception: " << e.what() << std::endl; }
		//std::cerr << "NapiAsyncWorker execute end" << std::endl;
	};

	void OnOK() {
		//std::cerr << "NapiAsyncWorker OnOK start" << std::endl;
		try { onOK(this); }
		catch (std::exception e) { std::cerr << "NapiAsyncWorker OnOK exception: " << e.what() << std::endl; }
		//std::cerr << "NapiAsyncWorker OnOK end" << std::endl;
	};
};

