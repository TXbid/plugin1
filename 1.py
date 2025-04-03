import os

def print_directory_structure(start_path="."):
    """
    遍历指定路径及其子文件夹，并打印所有目录和文件的完整路径。

    Args:
        start_path (str): 开始遍历的路径，默认为当前目录。
    """
    for root, dirs, files in os.walk(start_path):
        print(f"目录: {root}")
        for name in dirs:
            print(f"  子目录: {os.path.join(root, name)}")
        for name in files:
            print(f"  文件: {os.path.join(root, name)}")

if __name__ == "__main__":
    print_directory_structure()