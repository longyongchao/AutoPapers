import os
import json
import random
import requests
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler

from env import CUBOX_URL

# 配置
SUMMARIES_FOLDER = "/data/lyc/papers/ICLR_2024/sum"  # summaries 文件夹路径
PROCESSED_FILES_JSON = os.path.join(SUMMARIES_FOLDER, "processed_files.json")  # 存储已处理文件的 JSON 文件
API_URL = CUBOX_URL  # 替换为你的 API 链接
DEFAULT_FOLDER = f"ICLR 2024"  # 用户自定义收藏夹名称
MAX_CONTENT_LENGTH = 3000  # API 限制的最大内容长度


def load_processed_files():
    """
    加载已处理文件的记录。
    如果文件不存在，返回空集合。
    """
    if os.path.exists(PROCESSED_FILES_JSON):
        with open(PROCESSED_FILES_JSON, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()


def save_processed_files(processed_files):
    """
    保存已处理文件的记录。
    """
    with open(PROCESSED_FILES_JSON, "w", encoding="utf-8") as f:
        json.dump(list(processed_files), f, ensure_ascii=False, indent=4)


def get_random_files(folder, processed_files, n):
    """
    从文件夹中随机抽取未处理过的文件。

    Parameters:
        folder (str): 文件夹路径。
        processed_files (set): 已处理文件的集合。
        n (int): 要抽取的文件数量。

    Returns:
        list: 抽取到的文件列表。
    """
    all_files = [f for f in os.listdir(folder) if f.endswith(".md")]
    unprocessed_files = [f for f in all_files if f not in processed_files]

    if len(unprocessed_files) == 0:
        print("No unprocessed files available.")
        return []

    return random.sample(unprocessed_files, min(n, len(unprocessed_files)))


def call_api(file_path, folder):
    """
    调用 API 上传文件内容。

    Parameters:
        file_path (str): 文件路径。
        folder (str): 收藏夹名称。

    Returns:
        bool: 是否调用成功。
    """
    # 读取文件内容
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 截断内容以符合 API 限制
    if len(content) > MAX_CONTENT_LENGTH:
        content = content[:MAX_CONTENT_LENGTH]

    # 获取文件名作为标题
    title = os.path.splitext(os.path.basename(file_path))[0]

    # 构造请求体
    payload = {
        "type": "memo",
        "content": content,
        "title": title,
        "description": "",
        "tags": [],
        "folder": folder,
    }

    # 调用 API
    try:
        response = requests.post(API_URL, json=payload)
        response_data = response.json()

        if response.status_code == 200 and response_data.get("code") == 200:
            print(f"Successfully uploaded: {title}")
            return True
        else:
            print(f"Failed to upload {title}: {response_data}")
            return False
    except Exception as e:
        print(f"Error while uploading {title}: {e}")
        return False


def process_files(n, folder):
    """
    从 summaries 文件夹中随机抽取 n 个文件并调用 API 上传。

    Parameters:
        n (int): 要抽取的文件数量。
        folder (str): 收藏夹名称。
    """
    # 加载已处理文件
    processed_files = load_processed_files()

    # 获取随机抽取的文件
    random_files = get_random_files(SUMMARIES_FOLDER, processed_files, n)

    if not random_files:
        print("No files to process.")
        return

    # 处理每个文件
    for file_name in random_files:
        file_path = os.path.join(SUMMARIES_FOLDER, file_name)

        # 调用 API
        success = call_api(file_path, folder)

        # 如果调用成功，记录文件
        if success:
            processed_files.add(file_name)

    # 保存已处理文件记录
    save_processed_files(processed_files)
    print("Processing completed.")


def schedule_task(n, folder, debug=False):
    """
    定义每日定时任务，支持 Debug 模式立即运行。

    Parameters:
        n (int): 每日抽取的文件数量。
        folder (str): 收藏夹名称。
        debug (bool): 是否立即运行任务。
    """
    if debug:
        print("Debug mode: Running task immediately...")
        process_files(n, folder)
    else:
        scheduler = BlockingScheduler()

        # 每日凌晨 3 点运行
        scheduler.add_job(process_files, "cron", hour=3, minute=0, args=[n, folder])

        print("Scheduler started. Press Ctrl+C to exit.")
        try:
            scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            print("Scheduler stopped.")


if __name__ == "__main__":
    # 用户自定义参数
    n = 10  # 每日抽取的文件数量
    folder = DEFAULT_FOLDER  # 收藏夹名称

    # 是否启用 Debug 模式
    debug_mode = False  # 将此值设为 True 以立即运行任务

    # 启动任务
    schedule_task(n, folder, debug=debug_mode)
