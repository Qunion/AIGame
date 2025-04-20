import os


def generate_tree(path, prefix=''):
    items = os.listdir(path)
    items.sort()
    tree = []
    for index, item in enumerate(items):
        full_path = os.path.join(path, item)
        is_last = index == len(items) - 1
        if os.path.isdir(full_path):
            tree.append(prefix + ('└── ' if is_last else '├── ') + item + '/')
            new_prefix = prefix + ('    ' if is_last else '│   ')
            tree.extend(generate_tree(full_path, new_prefix))
        else:
            tree.append(prefix + ('└── ' if is_last else '├── ') + item)
    return tree


def get_available_filename(base_name, dir_name):
    base, ext = os.path.splitext(base_name)
    new_base = f"{base}_{dir_name}"
    new_name = f"{new_base}{ext}"
    index = 1
    while os.path.exists(new_name):
        new_name = f"{new_base}_{index}{ext}"
        index += 1
    return new_name


def export_tree_to_txt(directory, output_dir):
    try:
        tree = generate_tree(directory)
        base_filename = "文件目录导出.txt"
        dir_name = os.path.basename(os.path.normpath(directory))
        output_file = os.path.join(output_dir, get_available_filename(base_filename, dir_name))
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(os.path.abspath(directory) + '\n')
            f.write(dir_name + '\n')
            for line in tree:
                f.write(line + '\n')
        print(f"树状图已成功导出到 {output_file}")
    except FileNotFoundError:
        print(f"错误: 指定的目录 {directory} 未找到。")
    except Exception as e:
        print(f"错误: 发生了一个未知错误: {e}")


if __name__ == "__main__":
    input_directory = input("请输入要生成树状图的目录路径: ")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    export_tree_to_txt(input_directory, script_dir)
    