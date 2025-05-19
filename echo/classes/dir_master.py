import os
import shutil

class Dir_master:
    def __init__(self):
        pass

    def create_directory(self, dir_name):
        """Создаёт директорию. Если такая есть - удаляет старую."""
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)

        os.makedirs(dir_name)


    def move_file(self, src_file, dst_dir):

        if not os.path.isfile(src_file):
            return f"Dir_master: Исходный файл не существует: {src_file}"

        if not os.path.exists(dst_dir):
            return f"Dir_master: Не удалось найти директорию назначения {dst_dir}: {e}"

        dst_file = os.path.join(dst_dir, os.path.basename(src_file))

        try:
            shutil.move(src_file, dst_file)
            return True
        except Exception as e:
            return f"Dir_master: Ошибка при перемещении файла {src_file} -> {dst_file}: {e}"
