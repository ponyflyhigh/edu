import pyaudio
import dashscope
from dashscope.audio.tts_v2 import *
from http import HTTPStatus
from dashscope import Generation


charpter1='''
# 角色
你是一位英语交流大师，擅长与小朋友进行互动，通过固定的英文问题来文档内容。文档信息存储在知识库中${Retrieval_DDbD.result.chunkList.[content]}。要求全程英文交流。每次小朋友回答完可适当夸奖一下。

## 技能
### 技能1：互动提问
- 根据提供的问题列表，与小朋友进行互动。
- 用简单易懂的语言解释文档内容，并引导小朋友回答问题。
- 要求日常交流的词汇，不要过于复杂

### 技能3：适应性调整
- 根据小朋友的理解能力和反馈，适时调整提问方式和解释方法。
- 确保互动过程有趣且富有教育意义。

## 限制
- 仅使用知识库中的文档信息进行互动。
- 保持语言简单易懂，适合小朋友的理解水平。
- 保证互动过程积极健康，避免任何不当或敏感的话题。
-每次只提问一个问题，且禁止自问自答，
必须完成英文提问之后，然后用中文对小朋友的发音和语法语调来纠偏，给出适当建议，
- 每次提问，必须用相似语气简单来重复上一个内容(首个问题不用总结)，然后下个问题提问必须加上题号和问题，比如1.:Where is the rock?  按照给定的一致，不得随意更改，
-禁止输出中文和分析过程
- 首次对话简单说开场白之后，就提问第一个问题，且禁止给出答案，可以启发小朋友来思考
-每次回答不超过50词
问题列表：
1. Where is the rock?  
2. What is working on the rock?  


示例：
输入：hello
输出：hello，little friend .1. Where is the rock?  

输入：The rock is high on top of a mountain. It's like it's sitting there, enjoying the view from up high!


输出：yes,The rock is high on top of a mountain.So2. What is working on the rock?  


'''


model = "cosyvoice-v1"
voice = "longxiaochun"


class Callback(ResultCallback):
    _player = None
    _stream = None
    _text_buffer = ""  # 用于拼接流式输出的文本

    def on_open(self):
        self._player = pyaudio.PyAudio()
        self._stream = self._player.open(
            format=pyaudio.paInt16, channels=1, rate=22050, output=True
        )

    def on_complete(self):
        pass  # No need to print a completion message

    def on_error(self, message: str):
        pass  # No need to print error messages

    def on_close(self):
        self._stream.stop_stream()
        self._stream.close()
        self._player.terminate()

    def on_event(self, message):
        pass  # No need to print event messages

    def on_data(self, data: bytes) -> None:
        self._stream.write(data)

    def append_text(self, text: str):
        """ 拼接流式输出的文本 """
        self._text_buffer += text
        print(text, end="")

    def get_text(self):
        """ 获取拼接后的完整文本 """
        return self._text_buffer


def synthesizer_with_llm():
    callback = Callback()
    synthesizer = SpeechSynthesizer(
        model=model,
        voice=voice,
        format=AudioFormat.PCM_22050HZ_MONO_16BIT,
        callback=callback,
    )

    messages = [{"role": "user", "content": "hello"}]
    responses = Generation.call(
        model="qwen-turbo",
        messages=messages,
        result_format="message",
        stream=True,
        incremental_output=True,
    )
    
    for response in responses:
        if response.status_code == HTTPStatus.OK:
            text = response.output.choices[0]["message"]["content"]
            callback.append_text(text)  # 拼接流式输出的文本
            synthesizer.streaming_call(text)  # 传输当前文本给语音合成器
        else:
            # Handle error appropriately without print
            pass

    synthesizer.streaming_complete()

    # 获取拼接后的完整文本（如果需要的话）
    full_text = callback.get_text()


if __name__ == "__main__":
    synthesizer_with_llm()
