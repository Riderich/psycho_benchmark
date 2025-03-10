import json
import requests
import os
from tqdm import tqdm
import time
from openai import OpenAI

# 定义API配置（需要替换为你的实际API密钥和端点）
DEEPSEEK_API_KEY = "sk-b3fe31a92797482891ecf51cf43c2992"
DEEPSEEK_API_URL = "https://api.deepseek.com/v1"  # 或其他端点

# 定义分类维度
DIMENSIONS = [
    "身体健康导致的心理问题",
    "社会隔离（空巢）导致的心理问题",
    "认知功能衰退导致的心理问题",
    "退休导致的心理问题"
]

def load_json_data(file_path):
    """加载JSON文件并转换为Python对象"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"成功加载JSON文件，共包含 {len(data)} 条对话记录")
        return data
    except Exception as e:
        print(f"加载JSON文件时出错: {e}")
        return None

def call_deepseek_api(conversation_content):
    """调用DeepSeek-R1 API进行分类"""
    # 构建提示
    prompt = f"""
分析以下对话内容，判断是否符合以下四个维度之一：
1. 身体健康导致的心理问题
2. 社会隔离（空巢）导致的心理问题
3. 认知功能衰退导致的心理问题
4. 退休导致的心理问题

对话内容: 
问题: {conversation_content['instruction']}
问题详情: {conversation_content['input']}
回答: {conversation_content['output']}

请回答以下问题：
1. 这个对话是否符合以上四个维度中的任何一个?
2. 如果符合，它属于哪个维度?
3. 简要说明理由。

以JSON格式回答，格式如下:
{{
    "符合维度": true/false,
    "所属维度": "维度名称或空字符串",
    "理由": "简要解释"
}}
"""

    # headers = {
    #     "Content-Type": "application/json",
    #     "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
    # }
    
    # payload = {
    #     "model": "deepseek-chat",  # 或者你想使用的具体模型名称
    #     "messages": [
    #         {
    #             "role": "user",
    #             "content": prompt
    #         }
    #     ],
    #     "temperature": 0.1,  # 低温度以获得更确定的回答
    #     "max_tokens": 500
    # }

    try:
        # 使用OpenAI官方库调用API
        client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_API_URL)

        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "user", "content": prompt}
            ],
            stream=False
        )
        
        ai_response = response.choices[0].message.content
        
        # 尝试解析JSON响应
        try:
            return json.loads(ai_response)
        except:
            print(f"无法解析API响应为JSON: {json.loads(ai_response)}")
            return {"符合维度": False, "所属维度": "", "理由": "处理错误"}
            
    except Exception as e:
        print(f"API调用出错: {e}")
        return {"符合维度": False, "所属维度": "", "理由": f"API错误: {str(e)}"}

    
def mock_deepseek_api(conversation_content):
    """模拟API调用的函数，用于测试"""
    # 这里可以实现一些简单的规则来模拟分类
    instruction = conversation_content['instruction'].lower()
    input_text = conversation_content['input'].lower()
    
    # 简单模拟：检查是否包含关键词
    if '健康' in instruction or '健康' in input_text or '身体' in instruction or '身体' in input_text:
        return {
            "符合维度": True,
            "所属维度": "身体健康导致的心理问题",
            "理由": "对话中提到了健康相关问题"
        }
    elif '孤独' in instruction or '孤独' in input_text or '隔离' in instruction:
        return {
            "符合维度": True,
            "所属维度": "社会隔离（空巢）导致的心理问题",
            "理由": "对话中提到了孤独或隔离相关问题"
        }
    else:
        return {
            "符合维度": False,
            "所属维度": "",
            "理由": "不符合任何维度"
        }

def process_conversations(data, use_real_api=False):
    """处理所有对话，进行分类"""
    results = {dimension: [] for dimension in DIMENSIONS}
    
    for idx, item in enumerate(tqdm(data, desc="处理对话")):
        # 调用API或模拟函数
        if use_real_api:
            classification = call_deepseek_api(item)
            # 添加延迟以避免API速率限制
            time.sleep(1)
        else:
            classification = mock_deepseek_api(item)
        
        # 如果符合任何维度，添加到结果中
        if classification.get("符合维度", False):
            dimension = classification.get("所属维度", "")
            if dimension in DIMENSIONS:
                results[dimension].append({
                    "index": idx,
                    "conversation": item,
                    "理由": classification.get("理由", "")
                })
    
    return results

def save_results(results, output_dir="output"):
    """保存分类结果"""
    # 创建输出目录
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # 保存总结报告
    summary = {dimension: len(items) for dimension, items in results.items()}
    with open(f"{output_dir}/summary.json", 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    # 保存每个维度的详细结果
    for dimension, items in results.items():
        if items:  # 只保存非空结果
            filename = dimension.replace('（', '').replace('）', '').replace(' ', '_')
            with open(f"{output_dir}/{filename}.json", 'w', encoding='utf-8') as f:
                json.dump(items, f, ensure_ascii=False, indent=2)
    
    print(f"结果已保存到 {output_dir} 目录")
    print("分类结果摘要:")
    for dimension, count in summary.items():
        print(f"- {dimension}: {count} 条")

def main():
    # 设置文件路径
    json_file_path = "PsyQA_full.json"  # 更改为你的实际文件路径
    
    # 加载数据
    data = load_json_data(json_file_path)
    if not data:
        return
    
    # 询问用户是否使用真实API
    use_real_api = input("是否调用实际的DeepSeek API? (y/n): ").lower() == 'y'
    
    if use_real_api and DEEPSEEK_API_KEY == "your_api_key_here":
        print("请先在脚本中设置你的API密钥!")
        return
    
    # 处理对话
    results = process_conversations(data, use_real_api)
    
    # 保存结果
    save_results(results)

if __name__ == "__main__":
    main()