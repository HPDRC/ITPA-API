#include "utils.h"

using timeUnitMillis = long long;

timeUnitMillis timeNowMillis() {
	std::chrono::time_point<std::chrono::system_clock> now = std::chrono::system_clock::now();
	auto duration = now.time_since_epoch();
	auto millis = std::chrono::duration_cast<std::chrono::milliseconds>(duration).count();
	return (timeUnitMillis)millis;
};

void rgbFrameFromJpegMat(AVFrame &toFrame, cv::Mat &fromMat, unsigned int width, unsigned int height) {
	const unsigned char* curFrameDataStart = fromMat.datastart;
	unsigned int curFrameYOffset = 0, curFrameStride = 3 * width;

	auto rgbStride = toFrame.linesize[0];
	unsigned int rgbYOffset = 0;
	uint8_t *toFrameData = toFrame.data[0];

	for (unsigned int y = 0; y < height; ++y, rgbYOffset += rgbStride, curFrameYOffset += curFrameStride) {
		unsigned int xOffset = 0;
		for (unsigned int x = 0; x < width; ++x, xOffset += 3) {
			unsigned int toFramePixOffset = rgbYOffset + xOffset;
			unsigned int fromMatPixOffset = curFrameYOffset + xOffset;
			toFrameData[toFramePixOffset + 0] = curFrameDataStart[fromMatPixOffset + 2];
			toFrameData[toFramePixOffset + 1] = curFrameDataStart[fromMatPixOffset + 1];
			toFrameData[toFramePixOffset + 2] = curFrameDataStart[fromMatPixOffset + 0];
		}
	}
};

void FFmpegInitialize(void) {
	av_log_set_level(AV_LOG_ERROR);
	av_register_all();
};

static const int B64index[256] = { 0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0, 62, 63, 62, 62, 63, 52, 53, 54, 55,
56, 57, 58, 59, 60, 61,  0,  0,  0,  0,  0,  0,  0,  0,  1,  2,  3,  4,  5,  6,
7,  8,  9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25,  0,
0,  0,  0, 63,  0, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40,
41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51 };

std::string b64decode(const void* data, const size_t len) {
	unsigned char* p = (unsigned char*)data;
	int pad = len > 0 && (len % 4 || p[len - 1] == '=');
	const size_t L = ((len + 3) / 4 - pad) * 4;
	std::string str(L / 4 * 3 + pad, '\0');
	//unsigned char* pstr = (unsigned char*)str.c_str();

	for (size_t i = 0, j = 0; i < L; i += 4) {
		int n = B64index[p[i]] << 18 | B64index[p[i + 1]] << 12 | B64index[p[i + 2]] << 6 | B64index[p[i + 3]];
		/**pstr++ = n >> 16;
		*pstr++ = n >> 8 & 0xFF;
		*pstr++ = n & 0xFF;*/
		str[j++] = n >> 16;
		str[j++] = n >> 8 & 0xFF;
		str[j++] = n & 0xFF;
	}
	if (pad) {
		int n = B64index[p[L]] << 18 | B64index[p[L + 1]] << 12;
		str[str.size() - 1] = n >> 16;
		if (len > L + 2 && p[L + 2] != '=') {
			n |= B64index[p[L + 2]] << 6;
			str.push_back(n >> 8 & 0xFF);
		}
	}
	return str;
};

std::vector<uchar> cv_mat_to_vector(cv::Mat mat) {
	std::vector<uchar> theVector;
	if (mat.isContinuous()) {
		theVector.assign(mat.datastart, mat.dataend);
	}
	else {
		for (int i = 0; i < mat.rows; ++i) {
			theVector.insert(theVector.end(), mat.ptr<uchar>(i), mat.ptr<uchar>(i) + mat.cols);
		}
	}
	return theVector;
};

void ffmpegThreadRecord(
	std::mutex & curFrameAccess,
	std::atomic<bool> & workdone,
	queue <FrameInfo*>&frameInfos,
	int fps,
	unsigned int width,
	unsigned int height,
	SwsContext* swsCtx,
	AVFrame *rgbpic,
	AVFrame *yuvpic,
	bool needsClose,
	AVStream* pStream,
	AVFormatContext* pFormatContext
) {
	int64_t last_pts = -1;
	timeUnitMillis millisPerFrame = (timeUnitMillis)(1000 / fps);
	AVPacket pkt;
	AVRational fpsR = (AVRational) { 1, fps };

	while (!(workdone && frameInfos.empty())) {
		try {
			FrameInfo *fi = NULL;

			{
				std::unique_lock<std::mutex> lk(curFrameAccess);
				if (!frameInfos.empty()) { fi = frameInfos.front(); frameInfos.pop(); }
			}

			if (fi) {
				try {
					Mat rawData(1, fi->bufferLen, CV_8UC1, fi->buffer);
					Mat decodedImage = imdecode(rawData, CV_LOAD_IMAGE_COLOR);
					OffsetMillis frame_position_millis = fi->frame_position_millis;
					int64_t pts = frame_position_millis / millisPerFrame;

					if (pts <= last_pts) {
						std::cerr << "ffmpegThreadRecord: out of order frame: " << frame_position_millis << " pts: " << pts << " last pts: " << last_pts << std::endl;
						pts = 1 + last_pts;
					}
					rgbFrameFromJpegMat(*rgbpic, decodedImage, width, height);
					sws_scale(swsCtx, rgbpic->data, rgbpic->linesize, 0, height, yuvpic->data, yuvpic->linesize);

					av_init_packet(&pkt);
					pkt.data = NULL;
					pkt.size = 0;
					last_pts = yuvpic->pts = pts;

					int got_output;
					avcodec_encode_video2(pStream->codec, &pkt, yuvpic, &got_output);
					if (got_output) {
						av_packet_rescale_ts(&pkt, fpsR, pStream->time_base);
						pkt.stream_index = pStream->index;
						//av_interleaved_write_frame(pFormatContext, &pkt);
						av_write_frame(pFormatContext, &pkt);
						av_packet_unref(&pkt);
					}
				}
				catch (std::exception e) { std::cerr << "ffmpegThreadRecord record loop exception: " << e.what() << std::endl; }

				delete fi;
			}
		}
		catch (std::exception e) { std::cerr << "ffmpegThreadRecord record loop exception: " << e.what() << std::endl; }
	}

	try {
		for (int got_output = 1; got_output; ) {
			avcodec_encode_video2(pStream->codec, &pkt, NULL, &got_output);
			if (got_output) {
				av_packet_rescale_ts(&pkt, fpsR, pStream->time_base);
				pkt.stream_index = pStream->index;
				//av_interleaved_write_frame(pFormatContext, &pkt);
				av_write_frame(pFormatContext, &pkt);
				av_packet_unref(&pkt);
			}
		}
		av_write_trailer(pFormatContext);
		if (needsClose) { avio_closep(&pFormatContext->pb); }
		avcodec_close(pStream->codec);
		sws_freeContext(swsCtx);
		av_frame_free(&rgbpic);
		av_frame_free(&yuvpic);
		avformat_free_context(pFormatContext);
	}
	catch (std::exception e) { std::cerr << "ffmpegThreadRecord: cleanup post loop exception " << e.what() << std::endl; }
};

