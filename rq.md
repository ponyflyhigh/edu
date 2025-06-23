| 功能    | 推荐技术/工具                     | 说明          |
| ----- | --------------------------- | ----------- |
| 语音采集  | WebRTC getUserMedia         | 浏览器标准API    |
| 音频传输  | WebSocket                   | 双向通信，低延迟    |
| 后端ASR | DashScope Recognition（流式接口） | 实时音频转文字     |
| 大模型交互 | DashScope Generation（流式接口）  | 实时语义解析及回答生成 |
| 流式TTS | DashScope SpeechSynthesizer | 实时语音合成      |
| 前端播放  | Web Audio API               | 播放原始PCM音频流  |


websocket-->stt-->model-->tts-->websocket
音视频采集与传输：通过 WebRTC 实现音视频流的实时传输。
语音识别（ASR）：将用户语音转换为文本，传递给大模型。
大模型交互：调用火山引擎的 API，获取 AI 生成的回复文本。
语音合成（TTS）：将 AI 回复的文本转换为语音，播放给用户。
UI 交互：展示对话历史、控制通话状态（开始/结束通话）等。
————————————————

                            版权声明：本文为博主原创文章，遵循 CC 4.0 BY-SA 版权协议，转载请附上原文出处链接和本声明。
                        
原文链接：https://blog.csdn.net/luck332/article/details/148174072