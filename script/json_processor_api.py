import json
import requests
import os
from tqdm import tqdm
import time
from openai import OpenAI
# from rule_based_classifier import rule_based_classification

# 定义API配置（需要替换为你的实际API密钥和端点）
DEEPSEEK_API_KEY = "sk-b3fe31a92797482891ecf51cf43c2992"
DEEPSEEK_API_URL = "https://api.deepseek.com/v1"  # 或其他端点
TENCENT_API_KEY = "sk-S9S3CANDkrBVCm1N8GuCQADLb6lDudLGqZowbyJ9VnZxOukT"
TENCENT_API_URL = "https://api.lkeap.cloud.tencent.com/v1"


# 定义分类维度
DIMENSIONS = [
    "对年龄增长带来的死亡的恐惧导致的心理问题",
    "因年老空巢或社会隔离的孤独感导致的心理问题",
    "对慢性病治疗的焦虑导致的心理问题",
    "因退休脱离工作或跟不上时代的无用感导致的心理问题",
    "自理能力下降带来生活困难导致的心理问题"
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

def call_deepseek_api(conversation_content, max_retries=3):
    """调用DeepSeek-R1 API进行分类"""
    # 构建提示
    prompt = f"""
请仔细分析以下对话内容，判断其是否确实属于老年人心理问题的以下维度之一：
1. 对年龄增长带来的对死亡的恐惧导致的心理问题
2. 因年老空巢或社会隔离的孤独感导致的心理问题
3. 对慢性病治疗的焦虑导致的心理问题
4. 因退休脱离工作或跟不上时代的无用感导致的心理问题
5. 自理能力下降带来生活困难导致的心理问题

对话内容: 
问题: {conversation_content['instruction']}
问题详情: {conversation_content['input']}

请进行严格的判断，确保内容真实符合维度定义。回答以下问题：
1. 这个对话是否明确且真实地符合以上维度之一？
2. 如果符合，具体属于哪个维度？
3. 请详细说明判断理由，解释为什么符合或不符合该维度，尤其注意是否存在误判的可能。

以JSON格式回答，格式如下:
{{
    "符合维度": true/false,
    "所属维度": "维度名称或空字符串",
    "理由": "详细解释"
}}
"""

    for attempt in range(max_retries):
        try:
            # 使用OpenAI官方库调用API
            client = OpenAI(api_key=TENCENT_API_KEY, base_url=TENCENT_API_URL)

            response = client.chat.completions.create(
                model="deepseek-v3",
                messages=[
                    {"role": "user", "content": prompt}
                ],
                stream=False
            )
            
            response = response.choices[0].message.content
            ai_response = response[response.find("{"):response.find("}")+1]
            
            # 尝试解析JSON响应
            try:
                print(ai_response)
                return json.loads(ai_response)
            
            except json.JSONDecodeError:
                print("无法解析API响应为JSON")
                if attempt < max_retries - 1:
                    print(f"重试第 {attempt + 1} 次...")
                    time.sleep(1)  # 等待一秒后重试
                else:
                    return {"符合维度": False, "所属维度": "", "理由": "处理错误"}
                    
        except Exception as e:
            print(f"API调用出错: {e}")
            if attempt < max_retries - 1:
                print(f"重试第 {attempt + 1} 次...")
                time.sleep(1)  # 等待一秒后重试
            else:
                return {"符合维度": False, "所属维度": "", "理由": f"API错误: {str(e)}"}

    
# def mock_deepseek_api(conversation_content):
#     """模拟API调用的函数，用于测试"""
#     # 这里可以实现一些简单的规则来模拟分类
#     instruction = conversation_content['instruction'].lower()
#     input_text = conversation_content['input'].lower()
    
#     # 简单模拟：检查是否包含关键词
#     if '健康' in instruction or '健康' in input_text or '身体' in instruction or '身体' in input_text:
#         return {
#             "符合维度": True,
#             "所属维度": "对慢性病治疗的焦虑导致的心理问题",
#             "理由": "对话中提到了健康相关问题"
#         }
#     elif '孤独' in instruction or '孤独' in input_text or '隔离' in instruction:
#         return {
#             "符合维度": True,
#             "所属维度": "因年老空巢或社会隔离的孤独感导致的心理问题",
#             "理由": "对话中提到了孤独或隔离相关问题"
#         }
#     else:
#         return {
#             "符合维度": False,
#             "所属维度": "",
#             "理由": "不符合任何维度"
#         }

def process_conversations(data, use_real_api=False)-> list[2]:
    """处理所有对话，进行分类"""
    results_true= {dimension: [] for dimension in DIMENSIONS}
    results_false= {"":[]}
    
    for idx, item in enumerate(tqdm(data, desc="处理对话")):
        # 调用API或模拟函数
        if use_real_api:
            classification = call_deepseek_api(item)
            # 添加延迟以避免API速率限制
            time.sleep(0.1)
        # else:
        #     classification = mock_deepseek_api(item)
        
        # 如果符合任何维度，添加到结果中
        if classification.get("符合维度", False):
            dimension = classification.get("所属维度", "")
            if dimension in DIMENSIONS:
                results_true[dimension].append({
                    "index": idx,
                    "conversation": item,
                    "理由": classification.get("理由", "")
                })
        else:
            dimension = classification.get("所属维度", "")
            results_false[dimension].append({
                "index": idx,
                "conversation": item,
                "理由": classification.get("理由", "")
            })
        
    
    return [results_true,results_false]

def save_results(results1,results2, output_dir="output"):
    """保存分类结果"""
    # 创建输出目录
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # 保存总结报告
    summary = {dimension: len(items) for dimension, items in results1.items()}
    with open(f"{output_dir}/summary.json", 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    # 保存每个维度的详细结果
    for dimension, items in results1.items():
        if items:  # 只保存非空结果
            filename = dimension.replace('（', '').replace('）', '').replace(' ', '_')
            with open(f"{output_dir}/{filename}.json", 'w', encoding='utf-8') as f:
                json.dump(items, f, ensure_ascii=False, indent=2)

    # 保存false结果
    for dimension, items in results2.items():
        if items:  # 只保存非空结果
            filename = "false_result"
            with open(f"{output_dir}/{filename}.json", 'w', encoding='utf-8') as f:
                json.dump(items, f, ensure_ascii=False, indent=2)
    
    print(f"结果已保存到 {output_dir} 目录")
    print("分类结果摘要:")
    for dimension, count in summary.items():
        print(f"- {dimension}: {count} 条")

def main():
    # 设置文件路径
    json_file_path = "sampled_PsyQA_1k.json"  # 更改为你的实际文件路径
    
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
    save_results(results[0],results[1])

if __name__ == "__main__":
    main()