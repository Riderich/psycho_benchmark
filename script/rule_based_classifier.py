import json
import re
from tqdm import tqdm
import os
from json_processor_api import call_deepseek_api

# 定义分类维度
DIMENSIONS = [
    "对年龄增长带来的死亡的恐惧导致的心理问题",
    "因年老空巢或社会隔离的孤独感导致的心理问题",
    "对慢性病治疗的焦虑导致的心理问题",
    "因退休脱离工作或跟不上时代的无用感导致的心理问题",
    "自理能力下降带来生活困难导致的心理问题"
]

# 每个维度的关键词
KEYWORDS = {
    "对年龄增长带来的死亡的恐惧导致的心理问题": ["死亡", "死", "去世", "终结", "生命", "年老", "老去",
                              "衰老", "老年", "年纪大", "害怕", "恐惧"],
    
    "因年老空巢或社会隔离的孤独感导致的心理问题": ["孤独", "隔离", "空巢", "独居", "一个人", "寂寞", 
                              "无人", "家人离开", "子女", "远离", "独处", "远行", "分离", "分开", 
                              "搬走", "搬家", "空房子", "没朋友", "无朋友"],
    
    "对慢性病治疗的焦虑导致的心理问题": ["慢性病", "治疗", "焦虑", "担心", "害怕", "病", "疾病", 
                         "长期", "康复", "药物", "治疗方案", "医生", "医院"],
    
    "因退休脱离工作或跟不上时代的无用感导致的心理问题": ["退休", "离职", "不工作", "无聊", "空虚", 
                                 "退下来", "养老", "离开工作岗位", "不上班",  "退休金", "养老金", 
                                 "闲下来", "没事做", "工作结束", "下岗", "退居二线"],
    
    "自理能力下降带来生活困难导致的心理问题": ["自理能力", "生活困难", "无法自理", "依赖", "帮助", "照顾", 
                            "护理", "行动不便", "生活质量", "独立性", "困难"]
}

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

def rule_based_classification(conversation_content):
    """基于关键词的简单分类规则"""
    instruction = conversation_content['instruction'].lower()
    input_text = conversation_content['input'].lower()
    output_text = conversation_content['output'].lower()
    
    # 合并文本以便于关键词搜索
    full_text = instruction + " " + input_text + " " + output_text
    
    # 检查每个维度的关键词
    for dimension, keywords in KEYWORDS.items():
        matched_keywords = []
        for keyword in keywords:
            if keyword in full_text:
                matched_keywords.append(keyword)
        
        if matched_keywords:
            return {
                "符合维度": True,
                "所属维度": dimension,
                "理由": f"对话中包含与{dimension}相关的关键词: {', '.join(matched_keywords)}",
                "匹配关键词": matched_keywords
            }
    
    return {
        "符合维度": False,
        "所属维度": "",
        "理由": "不符合任何维度"
    }

def advanced_rule_based_classification(conversation_content):
    """更复杂的规则分类逻辑"""
    instruction = conversation_content['instruction'].lower()
    input_text = conversation_content['input'].lower()
    output_text = conversation_content['output'].lower()
    
    # 合并文本
    full_text = instruction + " " + input_text + " " + output_text
    
    # 为每个维度计算匹配分数
    dimension_scores = {}
    for dimension, keywords in KEYWORDS.items():
        matched_keywords = set()
        for keyword in keywords:
            if keyword in full_text:
                # 计算关键词出现的次数
                count = len(re.findall(r'\b' + re.escape(keyword) + r'\b', full_text))
                if count > 0:
                    matched_keywords.add(keyword)
        
        # 根据匹配的关键词数量计算分数
        score = len(matched_keywords) / len(keywords) if keywords else 0
        dimension_scores[dimension] = {
            "score": score,
            "matched_keywords": list(matched_keywords)
        }
    
    # 找出得分最高的维度
    best_dimension = max(dimension_scores.items(), key=lambda x: x[1]["score"])
    
    # 只有当分数超过阈值时才认为符合
    threshold = 0.05  # 可以调整这个阈值
    if best_dimension[1]["score"] > threshold:
        return {
            "符合维度": True,
            "所属维度": best_dimension[0],
            "理由": f"对话中包含与{best_dimension[0]}相关的关键词: {', '.join(best_dimension[1]['matched_keywords'])}",
            "匹配关键词": best_dimension[1]["matched_keywords"],
            "分数": best_dimension[1]["score"]
        }
    else:
        return {
            "符合维度": False,
            "所属维度": "",
            "理由": "不符合任何维度或匹配度不足",
            "最高分维度": best_dimension[0],
            "分数": best_dimension[1]["score"]
        }

def process_conversations(data, method="advanced", use_real_api=False):
    """处理所有对话，进行分类"""
    results = {dimension: [] for dimension in DIMENSIONS}
    rejected = []  # 存储被API否决的结果
    
    # 第一轮：规则基础筛选
    for idx, item in enumerate(tqdm(data, desc="规则基础筛选")):
        if method == "simple":
            classification = rule_based_classification(item)
        else:
            classification = advanced_rule_based_classification(item)
        
        if classification.get("符合维度", False):
            dimension = classification.get("所属维度", "")
            if dimension in DIMENSIONS:
                results[dimension].append({
                    "index": idx,
                    "conversation": item,
                    "理由": classification.get("理由", ""),
                    "匹配关键词": classification.get("匹配关键词", []),
                    "分数": classification.get("分数", None),
                    "初筛结果": True
                })
    
    # 第二轮：API精细筛选
    if use_real_api:
        for dimension in DIMENSIONS:
            if results[dimension]:
                filtered_results = []
                print(f"\n正在对维度 '{dimension}' 进行API精细筛选...")
                
                for item in tqdm(results[dimension]):
                    api_classification = call_deepseek_api(item["conversation"])
                    if api_classification.get("符合维度", False) and api_classification.get("所属维度") == dimension:
                        item["api_理由"] = api_classification.get("理由", "")
                        filtered_results.append(item)
                    else:
                        item["api_理由"] = api_classification.get("理由", "")
                        rejected.append(item)
                
                results[dimension] = filtered_results
    
    return results, rejected

def save_results(results, rejected, output_dir="rule_based_output"):
    """保存分类结果"""
    # 创建输出目录
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # 保存总结报告
    summary = {dimension: len(items) for dimension, items in results.items()}
    summary["被API否决数量"] = len(rejected)
    
    with open(f"{output_dir}/summary.json", 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    # 保存每个维度的详细结果
    for dimension, items in results.items():
        if items:
            filename = dimension.replace('（', '').replace('）', '').replace(' ', '_')
            with open(f"{output_dir}/{filename}.json", 'w', encoding='utf-8') as f:
                json.dump(items, f, ensure_ascii=False, indent=2)
    
    # 保存被API否决的结果
    if rejected:
        with open(f"{output_dir}/rejected_by_api.json", 'w', encoding='utf-8') as f:
            json.dump(rejected, f, ensure_ascii=False, indent=2)
    
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
    
    # 询问用户使用哪种分类方法
    method = input("使用哪种分类方法? (simple/advanced, 默认advanced): ").lower()
    if method != "simple":
        method = "advanced"
    
    # 询问用户是否使用真实API
    use_real_api = input("是否调用实际的DeepSeek API? (y/n): ").lower() == 'y'
    
    # 处理对话
    results, errors = process_conversations(data, method, use_real_api)
    
    # 保存结果
    save_results(results, errors)

if __name__ == "__main__":
    main()