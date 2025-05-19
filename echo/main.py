import os
import sys
import json
import datetime
import classes.mymslib as ms
import classes.dir_master as D_m
import classes.my_queue as My_Q

class Chulan():
    def __init__(self):
        self.ms_login = "admin@markustester" 
        self.ms_passwd = "qwerty"
        
        self.filename = None        # Имя файла вебхука
        self.webhk_pth = None       # Путь до вебхука
        self.webhk_data = None      # Данные вебхука
        self.event_log_pth = None   # Директория логирования евента
        self.jsons_pth = None       # Директория для json-ов
        self.ms_api = None          # Объект работы с API Моего Склада
        self.dir_master = None
        self.log_term = False       # Флаг дублирования лога в терминал


class Main():
    def __init__(self):
        self.root_dir = ".."
        self.log_dir = "logus"
        self.main_log = "main.log"
        self.logus_pth = f"{self.root_dir}/{self.log_dir}"
        self.big_log = f"{self.logus_pth}/{self.main_log}"

        # Объект-хранилище
        self.chln = Chulan()
        
        # Создаём журнал main
        self.temp_log = f"temp/{self.main_log}"
        if os.path.exists(self.temp_log):
            os.remove(self.temp_log)

        self.log = ms.get_logger(log_name=self.temp_log,
                                 logger_name="main",
                                 term=self.chln.log_term)
        self.log.info("Начало работы")

    def get_webhk(self):
        """Берём вебхук"""
        try:
            # 1) Берём имя файла вебхука из argv
            self.chln.filename = sys.argv[1]
            self.log.info(f"Получено имя файла вебхука: {self.chln.filename}")

            # 2) Формируем путь к файлу
            self.chln.webhk_pth = f"webhooks/{self.chln.filename}"

            # 3) Читаем JSON из файла
            with open(self.chln.webhk_pth, 'r', encoding='utf-8') as f:
                self.chln.webhk_data = json.load(f)
            self.log.info("Данные вебхука успешно взяты")

        except BaseException as e:
            self.log.error(e, exc_info=True)
            self.error_exit()

    def dir_creater(self):
        """Создаёт нужные директории"""

        # 1) Извлекаем имя (без расширения) для создания папки
        event_dir = os.path.splitext(self.chln.filename)[0]

        # 2) Сохраняем пути в chulan
        self.chln.event_log_pth = f"{self.logus_pth}/events/{event_dir}"
        self.chln.jsons_pth = f"{self.chln.event_log_pth}/jsons"

        # 3) Создаём директории
        dirs = [
            self.chln.event_log_pth,
            self.chln.jsons_pth
        ]

        for one_dir in dirs:
            self.log.info(f"Создаю директорию {one_dir}")
            self.chln.dir_master.create_directory(dir_name=one_dir)


    def error_exit(self):

        dt_str = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        base, ext = os.path.splitext(self.temp_log)  # -> ("temp/main", ".log")
        self.log.info
        # Собираем новое имя файла: "temp/main_error_2025-02-20_14-23-56.log"
        new_name = f"{base}_error_{dt_str}{ext}"
        self.merge_temp_into_big()

        if os.path.exists(self.temp_log):
            try:
                os.rename(self.temp_log, new_name)
            except Exception as e:
                pass

        sys.exit(1)


    def merge_temp_into_big(self):
        """
        Дописывает содержимое временного лога (self.temp_log)
        в конец большого лога (self.big_log),
        сделав перед этим два пустых отступа (строки).
        """
        try:
            if not os.path.exists(self.temp_log):
                self.log.warning(f"Файл {self.temp_log} не найден, пропускаем merge.")
                return

            self.log.info("Переношу временный лог в общий")
            
            # 1) Читаем временный лог
            with open(self.temp_log, 'r', encoding='utf-8') as f_temp:
                temp_content = f_temp.read()

            # 2) Открываем big_log для добавления
            with open(self.big_log, 'a', encoding='utf-8') as f_big:
                # 3) Два пустых переноса строки (отступа)
                f_big.write('\n\n')
                # 4) Дописываем содержимое временного лога
                f_big.write(temp_content)

        except Exception as e:
            self.log.error(e, exc_info=True)
            self.error_exit()

    def work(self):
        try:
            self.log.info("Получаю вебхук...")
            self.get_webhk()  # Получаем filename и webhk_data

            self.log.info("Создаю объект Dir_master.")
            self.chln.dir_master = D_m.Dir_master()

            self.log.info("Создаю директории...")
            self.dir_creater()

            # self.log.info("Перемещаем вебхук в папку jsons.")
            # self.chln.dir_master.move_file(src_file=self.chln.webhk_pth,
            #                           dst_dir=self.chln.jsons_pth)

            self.log.info("Создаю ms_api")
            self.chln.ms_api = ms.APIClient(us=self.chln.ms_login,
                                           pas=self.chln.ms_passwd)

            self.log.info("Создаю объект очереди Queue.")
            q = My_Q.Queue()
            
            self.log.info("Создаю журнал для My_Q.Queue.")
            q.log = ms.get_logger(log_name=f"{self.chln.event_log_pth}/my_queue.log",
                                  logger_name="my_queue",
                                  term=self.chln.log_term
                                  )
            q.log.info("Логгер объекта сохдан.")
            
            self.log.info("Queue передан объект Chulan.")
            q.chln = self.chln
            
            self.log.info("Запускаю Queue.check_webh.")
            q.check_webhk()
            
            self.log.info("Запускаю Queue.get_events.")
            q.get_events()
            
            # Запускаем обработку очереди
            q.queue()
            
            self.log.info("Обработка вебхука окончена")
            
            self.merge_temp_into_big()

        except Exception as e:
            self.log.error(e, exc_info=True)
            self.error_exit()


if __name__ == "__main__":
    main = Main()
    main.work()
