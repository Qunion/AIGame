import shutil
import os

def copy_and_rename_files(original_file, list_file):
    try:
        # 检查原始文件是否存在
        if not os.path.exists(original_file):
            print(f"原始文件 {original_file} 不存在。")
            return False
        # 检查列表文件是否存在
        if not os.path.exists(list_file):
            print(f"列表文件 {list_file} 不存在。")
            return False
        # 读取列表文件中的新文件名
        with open(list_file, 'r', encoding='utf-8') as f:
            new_names = f.read().splitlines()

        # 依次复制并重命名文件
        for new_name in new_names:
            try:
                shutil.copy2(original_file, new_name)
                print(f"已复制并命名为 {new_name}")
            except Exception as e:
                print(f"复制并命名为 {new_name} 时出错: {e}")
        return True
    except Exception as e:
        print(f"操作过程中出现错误: {e}")
        return False

if __name__ == "__main__":
    while True:
        original_file = input("请输入原始文件的路径: ").strip()
        if not original_file:
            print("输入的原始文件路径为空，请重新输入。")
            continue
        list_file = input("请输入包含新文件名列表的文件路径: ").strip()
        if not list_file:
            print("输入的列表文件路径为空，请重新输入。")
            continue

        if copy_and_rename_files(original_file, list_file):
            break

    input("\n按任意键继续...")
    