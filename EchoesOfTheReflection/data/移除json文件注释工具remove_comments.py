import re
import os


def remove_comments(json_content):
    # 移除 # 开头的注释
    json_content = re.sub(r'#.*', '', json_content)
    # 移除单行注释
    json_content = re.sub(r'//.*', '', json_content)
    # 移除多行注释
    json_content = re.sub(r'/\*.*?\*/', '', json_content, flags=re.DOTALL)
    return json_content


def process_json_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            json_content = file.read()
        json_content_without_comments = remove_comments(json_content)
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(json_content_without_comments)
        print(f"注释已从 {file_path} 中移除。")
        return True
    except FileNotFoundError:
        print(f"文件 {file_path} 未找到。")
        return False
    except Exception as e:
        print(f"处理文件 {file_path} 时发生错误: {e}")
        return False


def process_all_json_files_in_folder(folder_path):
    for root, _, files in os.walk(folder_path):
        for file in files:
            if file.endswith('.json'):
                file_path = os.path.join(root, file)
                process_json_file(file_path)


if __name__ == "__main__":
    try:
        current_folder = os.getcwd()
        while True:
            choice = input(f"是否要移除当前文件夹 {current_folder} 中所有 JSON 文件的注释？(Y/N): ").strip().lower()
            if choice in ['y', '是']:
                process_all_json_files_in_folder(current_folder)
                break
            elif choice in ['n', '否']:
                while True:
                    file_path = input("请输入要处理的 JSON 文件的路径: ")
                    if process_json_file(file_path):
                        break
                    else:
                        print("重新选择操作。")
                        break
            else:
                print("输入无效，请输入 Y 或 N。")
    except Exception as e:
        print(f"程序运行过程中出现错误: {e}")
    finally:
        input("\n按任意键继续...")
    