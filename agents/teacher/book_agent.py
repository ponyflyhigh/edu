from dashscope import MultiModalConversation

# 请用您的本地音频的绝对路径替换 ABSOLUTE_PATH/welcome.mp3
audio_file_path = "C:\\Users\\86132\\Desktop\\education\\output\\file1\\file1_full_audio.mp3"
messages = [
    {
        "role": "user",
        "content": [{"audio": audio_file_path}],
    }
]

response = MultiModalConversation.call(model="qwen-audio-asr-latest", messages=messages)
print(response)