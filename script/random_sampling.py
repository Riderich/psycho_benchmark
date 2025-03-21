import json
import random

# 读取JSON文件
with open('PsyQA_full.json', 'r', encoding='utf-8') as file:
    data = json.load(file)

# 确保数据是一个列表
if isinstance(data, list):
    # 随机挑选1000条记录
    sample_data = random.sample(data, 1000)
else:
    raise ValueError("JSON文件的顶层结构不是一个列表")

# 将挑选出的记录写入新的JSON文件
with open('sampled_PsyQA_1k.json', 'w', encoding='utf-8') as file:
    json.dump(sample_data, file, ensure_ascii=False, indent=4)

print("随机挑选的1000条记录已保存到'sampled_file.json'")