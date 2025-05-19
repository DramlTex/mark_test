import os
import sys
import json
import classes.mymslib as ms
from jmespath import search as rip
from classes.super_event_worker import Event_worker

class Queue:
    def __init__(self):
        """
        Инициализирует объект Queue, сохраняет ссылку на ms_api и log.
        Загружает вебхук, проверяет его и получает полные данные по событиям.
        """
        
        self.chln = None
        
        self.log = None  # Журнал
        self.ms_api = None  # Объект связи с Моим Складом
        self.events = None  # Все эвенты
        self.audit_href = None  # Ссылка аудита
        self.chenge_user = None  # Юзер сделавший изменения
        self.full_events = None  # Полные данные евентов

    def check_webhk(self):
        """
        Проверяет, что вебхук содержит необходимые поля:
        auditContext.meta.href, uid, events.
        Если нет — завершает работу с ошибкой.
        """
        self.log.info("Проверяю целостность вебхука")
        self.audit_href = rip("auditContext.meta.href", self.chln.webhk_data)
        self.chenge_user = rip("auditContext.uid", self.chln.webhk_data)
        self.events = rip("events", self.chln.webhk_data)
        
        if (self.audit_href is None or
            self.chenge_user is None or
            self.events is None):
            message = "Вебхук содержит не все должные поля."
            self.log.error(message)
            raise ValueError(message)

        self.log.info("Проверка пройденна.")


    def get_events(self):
        """
        По полученному audit_href загружает полные данные по событиям,
        сохраняет их в full_events.
        Если не удалось получить данные, завершается с ошибкой.
        """
        
        events_path = f"{self.chln.jsons_pth}/events.json"
        events_rows_path = f"{self.chln.jsons_pth}/events_rows.json"
        
        self.log.info("Получаю данные евентов.")
        url = self.audit_href + "/events"
        self.log.info(url)
        r = self.chln.ms_api.get(url=url)

        if r is None:
            message = "Не получилось получить полные данные по событиям"
            self.log.error(message)
            raise ValueError(message)
        
        self.chln.ms_api.save_to_json(filename=events_path,
                                     data=r)
        
        self.log.info(f"Ответ сохранён в {events_path}")
        self.full_events = r["rows"]
        
        self.chln.ms_api.save_to_json(filename=events_rows_path,
                                     data=self.full_events)
        
        self.log.info(f"full_events сохранён в {events_rows_path}")


    def queue(self):
        """
        Последовательно извлекает события из full_events, создаёт для каждого Event_worker
        и вызывает у него event_manager() для обработки. После обработки всех событий —
        логирует завершение и выходит.
        """
        event_N = 1
        while self.full_events:
            
            event = self.full_events.pop()
            
            self.log.info(f"Евент {event_N}")
            
            event_dir = (f"{self.chln.event_log_pth}/event_{event_N}")
            event_dir_jsons = f"{event_dir}/jsons"
            
            self.log.info(f"Создаю директорию {event_dir}")
            self.chln.dir_master.create_directory(dir_name=event_dir)
            self.log.info(f"Создаю директорию {event_dir_jsons}.")
            self.chln.dir_master.create_directory(dir_name=event_dir_jsons)
            self.log.info(f"Сохраняю данные евента.")
            self.chln.ms_api.save_to_json(filename=f"{event_dir_jsons}/event.json",
                                          data=event)
            
            entity_type = event.get("entityType", None)
            self.log.info(f"Тип документа в евенте: {entity_type}") 
        
            if entity_type == "invoiceout":
                self.log.info("Создаю объект Event_worker...")
                worker = Event_worker(event=event,
                                      ms_api=self.chln.ms_api)
                
                self.log.info("Создаю лог объект Event_worker...")
                worker.log = ms.get_logger(log_name=f"{event_dir}/worker_{event_N}.log",
                                           logger_name=f"event_worker_{event_N}",
                                           term=self.chln.log_term)
                
                self.log.info("Передаю объекту Event_worker его дирректории...")
                worker.event_dir = event_dir
                worker.event_dir_jsons = event_dir_jsons
                self.log.info("Запускаю Event_worker.start")
                worker.start()
                self.log.info("Запускаю Event_worker.event_manager")
                worker.event_manager()
            else:
               self.log.info("Не счёт покупателя (invoiceout), не обрабатываем")  
            
            event_N += 1
        else:
            self.log.info("Обработка вебхука окончена\n\n")
