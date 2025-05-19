import config
from copy import deepcopy

class Judge:
    """
    Второй класс:
      - Получает big-data (big_data) от Checker.
      - Принимает решения: какой статус поставить, какие галочки сбросить.
      - Вызывает методы Моего Склада (PUT, POST) для обновления документа.
    """
    
    def __init__(self, big_data, ms_api, log=None):
        """
        :param big_data: Словарь с результатами работы Checker (self.big_data).
        :param ms_api: Класс для взаимодействия с Мой Склад.
        :param log: Логгер (опционально).
        """
        self.ms_api = ms_api
        self.cg = config
        self.log = log
        
        self.d = {
            "Глобально": big_data["total"],
            "Рецептура": big_data["группы_товаров"]["Рецептура"],
            "Закупка": big_data["группы_товаров"]["Закупка"],
            "Прайс": big_data["группы_товаров"]["Прайс"],
            "Акция": big_data["группы_товаров"]["Акция"],
            "Статус": big_data["state_name"],
            "Галки": big_data["галки"],
            "Скидка_агента": big_data["скидка_агента"],
            "Статусы": big_data["states_data"],
            "id_счёта": big_data["invoiceout_id"],
            "Лист_изменений": big_data["changes_list"],
            "Остальные_группы_товаров": big_data["группы_товаров"]["Остальное"],
        }

        
        self.baze_url = "https://api.moysklad.ru/api/remap/1.2"
        self.entity_url = f"{self.baze_url}/entity"

    def run(self):
        self.log.info("Запущен метод run (Judge).")
        self.log.info(f'Текущий статус документа: "{self.d["Статус"]}".')
        if self.st_sogl_manager():        # Статус: "На согласование Менеджер"
            return
        if self.st_in_work():             # Статус: "В работе"
            return
        if self.st_price_technolog():     # Статус: "Цены Технолог"
            return
        if self.st_price_findir():        # Статус: "Цены Фин.директор"
            return
        if self.st_sogl_technolog():      # Статус: "На согласование Технолог"
            return
        if self.st_sogl_findir():         # Статус: "На согласование Фин.директор"
            return
        if self.st_sogl_rop():            # Статус: "На согласование РОП"
            return
        if self.st_soglasovan():          # Статус: "Согласован"
            return
    # ------------------------------------------------------------------------------
    # Ниже — методы вспомогательные (с префиксом s_)
    # ------------------------------------------------------------------------------

    def s_galka_check(self, galka_name):
        """Проверяет, была ли установлена галочка."""
        # Если галка действительно установлена (и есть в списке изменений)
        if galka_name in self.d["Лист_изменений"] and galka_name in self.d["Галки"]:
            if self.s_face_controll(galka=galka_name):
                self.log.info(f"Галочка '{galka_name}' установлена пользователем.")
                return True
            else:
                return False
        elif galka_name in self.d["Галки"]:
            self.s_galya(galks=[galka_name])  
            self.log.info(f"Сброс галки: {galka_name}.")
            return False

    def s_face_controll(self, galka):
        """
        (2) Реальная проверка прав пользователя — закомментированная версия.
        Если нужно подключить, раскомментируйте эту функцию
        (и закомментируйте заглушку).
         """
        return True
    #     changed_user = self.big_data.get("changed_user", None)
    #
    #     # Соответствие между именами галок в коде и на сервере
    #     galka_mapping = {
    #         self.cg."Счёт согласован. РОП": "ROP",
    #         self.cg."Счёт согласован. Финдиректор": "Purchaseman",
    #         self.cg."Счёт согласован. Технолог": "Techman",
    #         self.cg."Счёт согласован. Менеджер": "Manager"
    #     }
    #     server_galka = galka_mapping.get(galka)
    #     if not server_galka:
    #         self.log.warning(f"Неизвестная галка: {galka}")
    #         return False
    #
    #     # URL вашего PHP-скрипта
    #     url = "http://85.193.91.150/Soglasovator/employees/mark_vizer.php"
    #
    #     # Данные для POST-запроса
    #     data = {
    #         "uid": changed_user,  # uid пользователя
    #         "key": server_galka   # Галка для сервера (ROP, Purchaseman, Techman, Manager)
    #     }
    #
    #     response = self.ms_api.zapros("POST", url, data=data)
    #     self.log.info(f"Ответ от сервера для галки {server_galka}: {response}")
    #
    #     controll = response.get("result", False)
    #     if not controll:
    #         self.log.info(f"У пользователя {changed_user} нет прав на установку галки {server_galka}")
    #         # При отсутствии прав можно сбросить галку сразу
    #         self.s_galya(galks=[galka])
    #         return False
    #
    #     return True
        
    
    def s_galya(self, state_name=None, galks=None):
        """Устанавливает статус счёта (state_name) и/или сбрасывает указанные галочки (galks)."""
        self.log.info(f"Метод s_galya: state_name={state_name}, galks={galks}")
        data = {}
        # Если надо поменять статус
        if state_name:
            state_id = self.d["Статусы"][state_name]
            data["state"] = {
                "meta": {
                    "href": f"{self.entity_url}/invoiceout/metadata/states/{state_id}",
                    "metadataHref": f"{self.entity_url}/invoiceout/metadata",
                    "type": "state",
                    "mediaType": "application/json"
                }
            }
        if galks:
            shab = {
                "meta": {
                    "href": f"{self.entity_url}/invoiceout/metadata/attributes/",
                    "type": "attributemetadata",
                    "mediaType": "application/json"
                },
                "value": False
            }
            attributes = []
            for galka_name in galks:
                attr_id = self.cg.ATTR_ID[galka_name]
                one = deepcopy(shab)
                one["meta"]["href"] += attr_id
                one["value"] = False
                attributes.append(one)
            data["attributes"] = attributes
        output = self.ms_api.put(
            url=f"{self.entity_url}/invoiceout/{self.d['id_счёта']}",
            data=data
            )
        self.log.info(f"Обновление счёта в МойСклад: {output}")

        if state_name:
            self.log.info(f"Статус переведён на '{state_name}'.")
        if galks:
            self.log.info(f"Сброшены галочки: {galks}.")

# ------------------------------------------------------------------------------
# Методы работы со статусами (префикс st)
# ------------------------------------------------------------------------------
    def st_sogl_manager(self):
        if self.d["Статус"] == "На согласование Менеджер":
            if self.s_galka_check("Счёт согласован. Менеджер"):
                self.s_galya(state_name="В работе")
                return True
    
    def st_price_technolog(self):
        if self.d["Статус"] == "Цены Технолог":
            if self.s_galka_check("Счёт согласован. Технолог"):
                self.s_galya(state_name="В работе")
                return True
    
    def st_price_findir(self):
        if self.d["Статус"] == "Цены Фин.директор":
            if self.s_galka_check("Счёт согласован. Финдиректор"):
                self.s_galya(state_name="В работе")
                return True
    
    def st_sogl_technolog(self):
        if self.d["Статус"] == "На согласование Технолог":
            if self.s_galka_check("Счёт согласован. Технолог"):
                self.s_galya(state_name="В работе")
                return True
    
    def st_sogl_findir(self):
        if self.d["Статус"] == "На согласование Фин.директор":
            if self.s_galka_check("Счёт согласован. Финдиректор"):
                self.s_galya(state_name="В работе")
                return True
    
    def st_sogl_rop(self):
        if self.d["Статус"] == "На согласование РОП":
            if self.s_galka_check("Счёт согласован. РОП"):
                self.s_galya(state_name="В работе")
                return True
    
    def st_soglasovan(self):
        if self.d["Статус"] == "Согласован":
            if 'sum' in self.d["Лист_изменений"] or 'positions' in self.d["Лист_изменений"]:
                self.s_galya(
                    state_name="На согласование Менеджер",
                    galks=[
                        "Счёт согласован. РОП",
                        "Счёт согласован. Финдиректор",
                        "Счёт согласован. Менеджер",
                        "Счёт согласован. Технолог"
                    ]
                )
                return True
    
    def st_in_work(self):
        # Проверка статуса
        if self.d["Статус"] != "В работе":
            return False
        if self.d["Остальные_группы_товаров"]:
            self.log.info("Есть необрабатываеммые группы товаров")
            return True
        self.log.info("Проверка на технолога")
        if self.fs_technolog_check():
            return True
        self.log.info("Товары группы 'Акция'")
        if self.fs_akcia_check():
            return True
        self.log.info("Проверка на нулевую цену")
        if self.fs_null_price_check():
            return True
        self.log.info("Проверка на несоотвествие Цене со скидкой")
        if self.fs_price_for_sale_check():
            return True
        self.log.info("Проверка на соотвествие скидки контрагента")
        if self.fs_agent_sale_check():
            return True
        self.log.info("Проверка на соотвествие скидки с таблицей скидок")
        if self.fs_table_discount_check():
            return True
        self.log.info("Проверка скидки больше 10%")
        if self.fs_discount_more_10_check():
            return True
        self.log.info("Все проверки пройденны: Согласованно")
        self.s_galya(state_name="Согласован")
        return True
        
# ------------------------------------------------------------------------------
# Очень подчинёные методы (префикс fs)
# ------------------------------------------------------------------------------
    def fs_technolog_check(self):
        # Товары "Спецрецептура" отсуствют
        if not any(self.d["Рецептура"].values()):
            return False
        self.log.info("Есть группа товаров \"Спецрецептура\"")
        # Галка "Согласованно технолог" установленна
        if "Счёт согласован. Технолог" in self.d["Галки"]:
            self.log.info("Уже согласованно технологом")
            return False
        # Есть товары с ценой 0
        if self.d["Рецептура"]["нулевая_цена"]:
            self.log.info("Товар с ценой 0 - Цены Технолог")
            self.s_galya(state_name="Цены Технолог")
            return True
        # Цена не соотвествует "Цена со скидкой"
        if self.d["Рецептура"]["несоответсвие_цене_со_скидкой"]:
            self.log.info("Цена не соотвествует \"Цена со скидкой\" - На согласование Технолог")
            self.s_galya(state_name="На согласование Технолог")
            return True
        # У контрагента есть скидка?
        if self.d["Скидка_агента"] > 0:
            # Скидка в пределах скидки контрагента?
            if self.d["Рецептура"]["больше_скидки_агента"]:
                self.log.info("Скидка больше скидки агента - На согласование Технолог")
                self.s_galya(state_name="На согласование Технолог")
                return True
            else:
                return False
        else:
            # Скидка совпадает с таблицей скидой?
            if self.d["Рецептура"]["скидка_больше_табличной"]:
                self.log.info("Скидка больше табличной скидки - На согласование Технолог")
                self.s_galya(state_name="На согласование Технолог")
                return True
            # Есть скидка_больше_10%
            if self.d["Рецептура"]["скидка_больше_10%"]:
                self.log.info("Скидка больше 10% - На согласование Технолог")
                self.s_galya(state_name="На согласование Технолог")
                return True
    
    def fs_akcia_check(self):
        # Товары "Акция" отсуствют
        if not any(self.d["Акция"].values()):
            return False
        self.log.info("Есть группа товаров \"Акция\"")
        # Скидка отсуствует
        if self.d["Акция"]["максимальная_скидка"] == 0:
            self.log.info("Скидка у товаров группы \"Акция\" отсуствует")  
            return False
        #Галочка "Согласованно РОП" не установленна
        if "Счёт согласован. РОП" not in self.d["Галки"]:
            self.log.info("На согласование РОП")
            self.s_galya(state_name="На согласование РОП")
            return True
        #Галочка "Согласованно Фин.директор" не установленна
        if "Счёт согласован. Финдиректор" not in self.d["Галки"]:
            self.log.info("На согласование Финдиректор")
            self.s_galya(state_name="На согласование Фин.директор")
            return True
    
    def fs_null_price_check(self):
        # Если нулевых цен нет
        if not self.d["Глобально"]["нулевая_цена"]:
            self.log.info("Глобально товаров с нулевыми ценами нет")
            return False
        # Есть товар из группы "Закупка"
        if any(self.d["Закупка"].values()):
            self.log.info("На согласование Финдиректор")
            self.s_galya(state_name="Цены Фин.директор")
            return True
        else:
            # Ничего не делаем (нет подходящей группы)
            self.log.info("Ничего не делаем (нет подходящей группы)")
            return True
    
    def fs_price_for_sale_check(self):
        # Если нет несоотвествия "Цена со скидкой"
        if not self.d["Глобально"]["несоответсвие_цене_со_скидкой"]:
            self.log.info("Глобально несоответсвия цены \"Цене со скидой\" нет.")
            return False
        # Есть товар из группы "Закупка"
        if any(self.d["Закупка"].values()):
            self.log.info("Есть товар из группы \"Закупка\"")
            # Несоответствие цены и нет галочки "Согласовано Фин.Директор
            if (self.d["Закупка"]["несоответсвие_цене_со_скидкой"]
                and "Счёт согласован. Финдиректор" not in self.d["Галки"]):
                self.log.info("На согласование Финдиректор")
                self.s_galya(state_name="На согласование Фин.директор")
                return True
        # Есть товары из группы "Прайс"
        if any(self.d["Прайс"].values()):
            self.log.info("Есть товар из группы \"Прайс\"")
            # Несоответствие цены и нет галочки "Согласовано РОП"
            if (self.d["Прайс"]["несоответсвие_цене_со_скидкой"]
                and "Счёт согласован. РОП" not in self.d["Галки"]):
                self.log.info("На согласование РОП")
                self.s_galya(state_name="На согласование РОП")
                return True
            else:
                # Ничего не делаем (нет подходящей группы)
                self.log.info("Ничего не делаем (нет подходящей группы)")
                return True
    
    def fs_agent_sale_check(self):
        if self.d["Скидка_агента"] == 0:
            self.log.info("У контрагента отсуствует скидка")
            return False
        else:
            self.log.info(f"Скидка контрагента: {self.d['Скидка_агента']}")
        if not self.d["Глобально"]["больше_скидки_агента"]:
            self.log.info("Глобально скидки соотвествуют скидке контрагента")
            self.s_galya(state_name="Согласован")
            return True
        if any(self.d["Закупка"].values()):
            self.log.info("Есть товары группы \"Закупка\"")
            # Несоответствие скидки и нет галочки "Согласовано Фин.Директор"
            if (self.d["Закупка"]["больше_скидки_агента"]
                and "Счёт согласован. Финдиректор" not in self.d["Галки"]):
                self.log.info("На согласование Фин.директор")
                self.s_galya("На согласование Фин.директор")
                return True
        if "Счёт согласован. РОП" in self.d["Галки"]:
            if self.d["Глобально"]["скидка_больше_10%"]:
                if "Счёт согласован. Финдиректор" in self.d["Галки"]:
                    self.s_galya(state_name="Согласован")
                    self.log.info("Согласован")
                else:
                    self.log.info("На согласование Фин.директор")
                    self.s_galya("На согласование Фин.директор")
            else:
                self.s_galya(state_name="Согласован")
                self.log.info("Согласован")
            return True
        else:
            self.s_galya(state_name="На согласование РОП")
            self.log.info("На согласование РОП")
            return True
    
    def fs_table_discount_check(self):
        # Скидка соответствует табличной
        if not self.d["Глобально"]["скидка_больше_табличной"]:
            self.log.info("Глобально несоответсвия табличной скидке нет.")
            return False
        # Есть товар из группы "Закупка"
        if any(self.d["Закупка"].values()):
            self.log.info("Есть товары группы \"Закупка\"")
            # Скидка не соответствует табличной и нет галочки "Согласовано Фин.Директор"
            if (self.d["Закупка"]["скидка_больше_табличной"]
                and "Счёт согласован. Финдиректор" not in self.d["Галки"]):
                self.log.info("На согласование Фин.директор")
                self.s_galya(state_name="На согласование Фин.директор")
                return True
        # Нет галочки "Согласовано РОП"
        if "Счёт согласован. РОП" not in self.d["Галки"]:
            self.s_galya(state_name="На согласование РОП")
            self.log.info("На согласование РОП")
            return True
    
    def fs_discount_more_10_check(self):
        # Скидка меньше 10%
        if not self.d["Глобально"]["скидка_больше_10%"]:
            self.log.info("Глобально скидки боль 10% нет.")
            return False
        else:
            self.s_galya(state_name="Согласован")
            self.log.info("Согласован")
        # Есть товары из группы "Прайс"?
        if any(self.d["Прайс"].values()):
            self.log.info("Есть товар из группы \"Прайс\"")
            # скидка_больше_10% и нет галочки "Согласовано РОП"
            if (self.d["Прайс"]["скидка_больше_10%"]
                and "Счёт согласован. РОП" not in self.d["Галки"]):
                self.s_galya(state_name="На согласование РОП")
                self.log.info("На согласование РОП")
                return True
        # Нет галочки "Согласовано Фин.Директор"
        if "Счёт согласован. Финдиректор" not in self.d["Галки"]:
            self.s_galya(state_name="На согласование Фин.директор")
            self.log.info("На согласование Фин.директор")
            return True
        else:
            self.s_galya(state_name="Согласован")
            self.log.info("Согласован")