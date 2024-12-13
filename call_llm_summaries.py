import os
import re
from typing import Optional
import ollama

summarizes_paper = """
You are an experienced scientist. 
Your task is to summarize a paper in the field of deep learning. 
Please respond in clear, concise, and easy-to-understand language. 
Here are my specific requirements:

* The core topic of the paper: Summarize the theme or research question of the paper in one sentence.
* Main contributions: What problems does the paper solve? What new methods or insights does it propose?
* Core methods: Describe the main technical methods or algorithms proposed in the paper using simple language.
* Conclusion: Summarize the overall significance or value of this paper in one sentence.

Here is the full content of the paper:

{paper_partial_content}
"""

# 定义调用 Ollama API 的函数
def call_llm(prompt: str, model: str = 'qwen2.5:72b-32k') -> Optional[str]:
    """
    调用 Ollama API 生成语言模型的响应。

    Parameters:
        prompt (str): 提示词，传递给语言模型。
        model (str): 使用的模型名称，默认为 'qwen2.5:72b-32k'。

    Returns:
        Optional[str]: 模型生成的响应内容，如果调用失败则返回 None。
    """
    try:
        # 调用 Ollama API
        result = ollama.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
        )
        response: str = result['message']['content']
        return response
    except Exception as e:
        print(f"Error in LLM call: {e}")
        return None


def extract_abstract(md_content: str) -> Optional[str]:
    """
    从 Markdown 文件内容中提取 `# Abstract` 部分的内容。

    Parameters:
        md_content (str): Markdown 文件的内容。

    Returns:
        Optional[str]: `# Abstract` 部分的内容，如果未找到则返回 None。
    """
    # 使用正则表达式匹配 `# Abstract` 和其后的内容，直到下一个标题（如 `# 1 INTRODUCTION`）
    match = re.search(r'#\s*Abstract\s*(.*?)\n(?=#|\Z)', md_content, re.IGNORECASE | re.DOTALL)
    if match:
        # 提取 Abstract 部分的内容，去掉首尾空白
        return match.group(1).strip()
    else:
        return None


def preprocess_markdown_content(md_content: str) -> str:
    """
    预处理 Markdown 文件内容：
    1. 截取前三分之一的内容。
    2. 移除图片链接。

    Parameters:
        md_content (str): 原始 Markdown 文件内容。

    Returns:
        str: 预处理后的 Markdown 内容。
    """
    # 移除图片链接（匹配 ![](...) 格式）
    md_content = re.sub(r'!\[.*?\]\(.*?\)', '', md_content)

    # 按行分割文件，截取前三分之一的内容
    lines = md_content.splitlines()
    one_third_length = max(1, len(lines) // 3)  # 至少保留一行
    partial_content = "\n".join(lines[:one_third_length])

    return partial_content


def summarize_markdown_files(md_folder: str, output_folder: str, model: str = 'qwen2.5:72b-32k'):
    """
    遍历指定文件夹中的所有 Markdown 文件，调用 LLM 对其内容进行总结，并保存总结结果。

    Parameters:
        md_folder (str): 包含 Markdown 文件的文件夹路径。
        output_folder (str): 保存总结结果的文件夹路径。
        model (str): 使用的语言模型名称，默认为 'qwen2.5:72b-32k'。

    Returns:
        None
    """
    # 确保输出文件夹存在
    os.makedirs(output_folder, exist_ok=True)

    # 获取文件夹中所有 Markdown 文件
    md_files = [f for f in os.listdir(md_folder) if f.endswith('.md')]
    print('count of md_files:', len(md_files))

    if not md_files:
        print("No Markdown files found in the specified folder.")
        return

    # 遍历每个 Markdown 文件
    for idx, md_file in enumerate(md_files):
        md_path = os.path.join(md_folder, md_file)
        output_path = os.path.join(output_folder, md_file)

        # 检查是否已经存在对应的输出文件
        if os.path.exists(output_path):
            print(f"😓 Output already exists for {md_file}, skipping...")
            continue

        try:
            # 读取 Markdown 文件内容
            with open(md_path, 'r', encoding='utf-8') as f:
                md_content = f.read()

            # 提取 `# Abstract` 部分内容
            abstract_content = extract_abstract(md_content)
            if not abstract_content:
                print(f"😓 No Abstract found in {md_file}. Skipping Abstract appending.")

            # 预处理 Markdown 文件内容
            partial_content = preprocess_markdown_content(md_content)

            # 构造提示词
            prompt = summarizes_paper.format(paper_partial_content=partial_content)

            # 调用 LLM 生成总结
            print(f"🔥 Summarizing: {md_file}...")
            summary = call_llm(prompt, model=model)

            if summary:
                # 保存总结结果
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(md_file.split('.')[0])
                    f.write("\n\n")
                    f.write(summary)

                    # 如果有 Abstract 内容，将其追加到文件末尾
                    if abstract_content:
                        f.write("\n\n# Abstract\n")
                        f.write(abstract_content)

                print(f"✅ [{idx}/{len(md_files)}] Summary saved to: {output_path}")
            else:
                print(f"❌ Failed to summarize: {md_file}")

        except Exception as e:
            print(f"Error processing file {md_file}: {e}")

    print("Summarization completed for all files.")


if __name__ == "__main__":
    # 示例路径
    md_folder = "/data/lyc/papers/ICLR_2024/md"  # 替换为 Markdown 文件所在的文件夹路径
    output_folder = "/data/lyc/papers/ICLR_2024/sum"  # 替换为总结结果保存的文件夹路径
    model = "llama3.1:70b-32k"  # 使用的语言模型

    summarize_markdown_files(md_folder, output_folder, model)
