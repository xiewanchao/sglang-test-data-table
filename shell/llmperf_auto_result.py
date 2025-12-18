"""
本脚本用于批量读取多个文件夹中的 *_summary.json 结果文件，提取模型名称、输入/输出 token 数、
并发数，以及多项延迟指标（TTFT、ITL、E2E），并最终将所有数据整理为一个按参数排序的 xlsx 文件。

主要功能：
1. 自动定位脚本所在目录，并在指定的多个文件夹中搜索以 `_summary.json` 结尾的文件；
2. 从 JSON 中提取关键性能字段，并将 ITL 从秒转换为毫秒；
3. 合并多个文件夹的数据，按输入长度 → 输出长度 → 并发数进行排序对齐；
4. 生成最终的汇总 CSV 文件（文件名以多个文件夹名称拼接生成）。

使用方法：
- 将本脚本放在 unified-cache-management/test/results 目录下
- 在 `folder_names` 中放入需要读取的文件夹名称（默认是llmperf文件夹）；
- 确保每个文件夹内包含格式正确的 `_summary.json` 文件；
- 运行脚本后会在同一目录下生成 `<folder1>_<folder2>_summary_results.xlsx`。
"""
import os
import json
import pandas as pd

# 获取当前脚本所在的目录
current_dir = os.path.dirname(os.path.abspath(__file__))

# 定义多个文件夹路径（这里可以放多个）
folder_names = ['recaculation']  # 可以改为 ['unifiedcache', 'nocache', 'baseline']

# 延迟字段顺序：TTFT → ITL → E2E
latency_fields = [
    'results_ttft_s_mean',
    'results_inter_token_latency_s_mean',
    'results_end_to_end_latency_s_mean'
]

def process_folder(folder_name):
    folder_path = os.path.join(current_dir, folder_name)
    data = []

    for filename in os.listdir(folder_path):
        if filename.endswith('_summary.json'):
            file_path = os.path.join(folder_path, filename)

            with open(file_path, 'r') as file:
                content = json.load(file)

            result = {}
            result['file_name'] = filename
            result['folder_name'] = folder_name   
            result['model'] = content.get('model', '')
            result['mean_input_tokens'] = content.get('mean_input_tokens', None)
            result['mean_output_tokens'] = content.get('mean_output_tokens', None)
            result['concurrent_requests'] = content.get('concurrent_requests', None)

            for field in latency_fields:
                value = content.get(field, None)
                if value is not None:
                    if field in ['results_inter_token_latency_s_mean']:
                        result[field] = value * 1000  # 转 ms
                    else:
                        result[field] = value
                else:
                    result[field] = None

            data.append(result)

    df = pd.DataFrame(data)
    return df


# 收集所有文件夹的数据
all_dfs = []
for folder_name in folder_names:
    df_folder = process_folder(folder_name)
    if not df_folder.empty:
        all_dfs.append(df_folder)

if not all_dfs:
    print("没有从任何文件夹中读取到数据，请检查文件夹路径和 JSON 文件。")
else:
    # 合并多个文件夹的数据
    combined_df = pd.concat(all_dfs, ignore_index=True)

    # 排序方式：输入长度 → 输出长度 → 并发数（完成对齐）
    combined_df_sorted = combined_df.sort_values(
        by=['folder_name', 'concurrent_requests', 'mean_input_tokens']
    )

    # 最终列顺序
    desired_cols = [
        'folder_name',  
        'file_name',
        'model',
        'mean_input_tokens',
        'mean_output_tokens',
        'concurrent_requests',
        'results_ttft_s_mean',
        'results_inter_token_latency_s_mean',
        'results_end_to_end_latency_s_mean'
    ]

    # 过滤掉不存在的列
    existing_cols = [c for c in desired_cols if c in combined_df_sorted.columns]
    final_df = combined_df_sorted[existing_cols]

    # 输出 CSV
    folder_prefix = "_".join(folder_names)
    output_file = f'{folder_prefix}_summary_results.csv'
    final_df.to_csv(output_file, index=False)

    # 输出excel
    # folder_prefix = "_".join(folder_names)
    # output_file = f'{folder_prefix}_summary_results.xlsx'
    # final_df.to_excel(output_file, index=False)

    print(f"数据成功合并并已添加文件夹名列，已输出 CSV：{output_file}")