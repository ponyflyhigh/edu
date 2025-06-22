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


import os
from dashscope import Generation

# 定义你的章节内容和问题
messages = [
    {'role': 'system', 'content': charpter1},
    {'role': 'user', 'content': 'hello little friend. 1. Where is the rock? '}
]

# 发起请求
responses = Generation.call(
    # 若没有配置环境变量，请用阿里云百炼API Key将下行替换为：api_key="sk-xxx",
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    model="qwen-plus",  # 此处以qwen-plus为例，您可按需更换模型名称
    messages=messages,
    result_format='message',
    stream=True,  # 增量式流式输出
    incremental_output=True
)

# 用于存储拼接后的完整内容
full_content = ""

# 逐步拼接流式输出内容
for response in responses:
    # 获取当前响应内容
    current_content = response.output.choices[0].message.content
    
    # 拼接到 full_content
    full_content += current_content
    
    # 输出当前内容（逐步输出）
    print(current_content)



