import config
from copy import deepcopy

class Judge:
    """
    Второй класс:
      - Получает big-data (big_data) от Checker.
      - Принимает решения: какой статус поставить, какие галочки сбросить.
      - Вызывает методы Моего Склада (PUT, POST) для обновления документа.
    """
    
    def __init__(self, big_data: dict, ms_api, log=None):
        """
        :param big_data: Словарь с результатами работы Checker (self.big_data).
        :param ms_api: Класс для взаимодействия с Мой Склад.
        :param log: Логгер (опционально).
        """
        self.big_data = big_data
        self.ms_api = ms_api
        self.log = log
        self.cg = config  # Ссылка на общую конфигурацию, если нужно

    def event_manager(self):
        """
        Основной метод принятия решения:
         - Опирается на текущий статус (state_name из big_data)
         - Анализирует флаги по группам (presence, null_price, price_matching, ...)
         - Решает, куда перебросить счёт (какой статус) или какие галочки сбросить.
        """
        self.log.info("Запущен метод event_manager (Judge).")

        # Для удобства — сразу получаем нужные значения из big_data
        invoiceout_id = self.big_data.get("invoiceout_id")
        state_name = self.big_data.get("state_name")

        # Если нет id счёта или state_name, считаем данные «битые»
        if not invoiceout_id or not state_name:
            self.log.error("Недостаточно данных (invoiceout_id или state_name отсутствуют). Отмена.")
            return

        self.log.info(f'Текущий статус документа: "{state_name}".')
        
        # == Логика переключения статусов ==

        # Статус: "На согласование Менеджер"
        if state_name == self.cg.ST_N_SOG_MANAGER:
            if self.s_galka_check(self.cg.G_N_MANAGER):
                self.s_in_work()

        # Статус: "В работе"
        elif state_name == self.cg.ST_N_IN_WORK:
            groups = self.big_data.get("groups_data", {})

            for group_name, group_info in groups.items():
                if not group_info.get("presence", False):
                    continue
                
                self.log.info(f"Проверяем группу '{group_name}'...")

                # ------------------------------------------------------------------------
                # Здесь мы извлекаем несколько полей из group_info.
                # Каждое поле - булевый флаг, показывающий "проблемный" момент в группе.
                # ------------------------------------------------------------------------
                
                # 1. null_price:
                #    True, если в группе есть хотя бы одна позиция с нулевой ценой.
                #    False - если у всех позиций > 0
                group_null_price = group_info.get("null_price", False)
                
                # 2. price_mismatch:
                #    True, если в группе есть хотя бы одна позиция с несоответствием цены
                #    (другими словами, фактическая цена позиции != "цена со скидкой").
                #    В group_info хранится флаг "price_matching" (True/False),
                #    но мы переворачиваем его в "group_price_mismatch":
                #    - Если price_matching=False (нет совпадения) => mismatch=True.
                #    - Если price_matching=True  (цены совпали) => mismatch=False.
                group_price_mismatch = not group_info.get("price_matching", True)

                # 3. discount_more_10:
                #    True, если в группе есть хотя бы одна позиция со скидкой > 10%.
                #    False, если скидки <= 10% или позиций нет.
                group_discount_more_10 = group_info.get("discount_more_10", False)

                # 4. discount_matching:
                #    True, если фактическая скидка не превышает скидку контрагента
                #    (т.е. согласована/допустима).
                #    False, если скидка в каком-то товаре превысила разрешённую контрагенту.
                group_discount_matching = group_info.get("discount_matching", True)

                # 5. normal_discount:
                #    True, если скидка в пределах "допустимой таблицы" (по внутренним правилам).
                #    False, если скидка выходит за эти пределы.
                group_normal_discount = group_info.get("normal_discount", True)

                # ------------------------------------------------------------------------
                # Дальше идёт логика проверки: если какой-то флаг свидетельствует о проблеме,
                # мы переводим счёт на согласование к нужному ответственному (при условии,
                # что галочка ответственного ещё не стоит).
                # ------------------------------------------------------------------------  


                # -----------------------------------------------------------------
                # 1) Нулевая цена
                # -----------------------------------------------------------------
                if group_null_price:
                    if group_name == "Рецептура":
                        if not self.big_data.get("galki", {}).get(self.cg.G_N_TECHNOLOG, False):
                            self.s_galya(state_name=self.cg.ST_N_PRC_TECHNOLOG)
                            return
                        else:
                            self.log.info("В группе 'Рецептура' нулевая цена, но галка Технолога уже стоит, пропускаем.")
                    elif group_name == "Закупка":
                        if not self.big_data.get("galki", {}).get(self.cg.G_N_FINDIR, False):
                            self.s_galya(state_name=self.cg.ST_N_PRC_FINDIR)
                            return
                        else:
                            self.log.info("В группе 'Закупка' нулевая цена, но галка Фин.директора уже стоит, пропускаем.")
                    else:
                        self.log.info(f"Группа '{group_name}' содержит нулевую цену, но не 'Рецептура' или 'Закупка'.")
                        # При необходимости другая логика: перевод на др. статус и return
                    continue

                # -----------------------------------------------------------------
                # 2) Несоответствие цены
                # -----------------------------------------------------------------
                if group_price_mismatch:
                    self.log.info(f"В группе '{group_name}' обнаружено несоответствие цены!")
                    if group_name == "Рецептура":
                        if not self.big_data.get("galki", {}).get(self.cg.G_N_TECHNOLOG, False):
                            self.s_galya(state_name=self.cg.ST_N_SOG_TECHNOLOG)
                            return
                        else:
                            self.log.info("Несоответствие цены в 'Рецептура', но галка Технолога уже есть, пропускаем.")
                    elif group_name == "Закупка":
                        if not self.big_data.get("galki", {}).get(self.cg.G_N_FINDIR, False):
                            self.s_galya(state_name=self.cg.ST_N_SOG_FINDIR)
                            return
                        else:
                            self.log.info("Несоответствие цены в 'Закупка', но галка Фин.директора уже есть, пропускаем.")
                    elif group_name == "Прайс":
                        if not self.big_data.get("galki", {}).get(self.cg.G_N_ROP, False):
                            self.s_galya(state_name=self.cg.ST_N_SOG_ROP)
                            return
                        else:
                            self.log.info("Несоответствие цены в 'Прайс', но галка РОП уже стоит, пропускаем.")
                    else:
                        self.log.info(f"В группе '{group_name}' несоответствие цены, но нет отдельного ответственного.")
                    continue

                # -----------------------------------------------------------------
                # 3) Проблемы со скидкой
                #    (здесь можно объединить логику 3.1, 3.2, 3.3 
                #     или обработать отдельно каждую)
                # -----------------------------------------------------------------
                
                # 3.1) Скидка не совпадает со скидкой контрагента
                if not group_discount_matching:
                    self.log.info(f"Группа '{group_name}': скидка не совпадает со скидкой контрагента.")
                    
                    # Допустим, если это "Закупка" => Фин.директор
                    # Если "Прайс" => РОП
                    # Если "Рецептура" => Технолог
                    if group_name == "Закупка":
                        if not self.big_data.get("galki", {}).get(self.cg.G_N_FINDIR, False):
                            self.s_galya(state_name=self.cg.ST_N_SOG_FINDIR)
                            return
                        else:
                            self.log.info("Скидка не совпадает (Закупка), но Фин.директор уже согласовал.")
                    elif group_name == "Прайс":
                        if not self.big_data.get("galki", {}).get(self.cg.G_N_ROP, False):
                            self.s_galya(state_name=self.cg.ST_N_SOG_ROP)
                            return
                        else:
                            self.log.info("Скидка не совпадает (Прайс), но РОП уже согласовал.")
                    elif group_name == "Рецептура":
                        if not self.big_data.get("galki", {}).get(self.cg.G_N_TECHNOLOG, False):
                            self.s_galya(state_name=self.cg.ST_N_SOG_TECHNOLOG)
                            return
                        else:
                            self.log.info("Скидка не совпадает (Рецептура), но Технолог уже согласовал.")
                    else:
                        self.log.info(f"Группа '{group_name}' скидка не совпадает, нет отдельной логики.")
                    
                    # Если дошли сюда — проверим следующую группу
                    continue

                # 3.2) Скидка > 10%
                if group_discount_more_10:
                    self.log.info(f"Группа '{group_name}' имеет скидку > 10%.")
                    
                    # Допустим, если >10% в "Закупка" => Фин.директор
                    if group_name == "Закупка":
                        if not self.big_data.get("galki", {}).get(self.cg.G_N_FINDIR, False):
                            self.s_galya(state_name=self.cg.ST_N_SOG_FINDIR)
                            return
                        else:
                            self.log.info("Скидка >10% (Закупка), но Фин.директор уже согласовал.")
                    # Если >10% в "Прайс" => РОП
                    elif group_name == "Прайс":
                        if not self.big_data.get("galki", {}).get(self.cg.G_N_ROP, False):
                            self.s_galya(state_name=self.cg.ST_N_SOG_ROP)
                            return
                        else:
                            self.log.info("Скидка >10% (Прайс), но РОП уже согласовал.")
                    # Если >10% в "Рецептура" => Технолог (пример, возможно у вас другая логика)
                    elif group_name == "Рецептура":
                        if not self.big_data.get("galki", {}).get(self.cg.G_N_TECHNOLOG, False):
                            self.s_galya(state_name=self.cg.ST_N_SOG_TECHNOLOG)
                            return
                        else:
                            self.log.info("Скидка >10% (Рецептура), но Технолог уже согласовал.")
                    else:
                        self.log.info(f"Группа '{group_name}': скидка > 10%, не нашли ответственного.")
                    
                    continue

                # 3.3) Скидка вне допустимой таблицы (normal_discount = False)
                if not group_normal_discount:
                    self.log.info(f"Группа '{group_name}' имеет скидку вне допустимой таблицы.")
                    # Аналогичная логика: смотрим, чья это группа => переводим на согласование

                    if group_name == "Прайс":
                        if not self.big_data.get("galki", {}).get(self.cg.G_N_ROP, False):
                            self.s_galya(state_name=self.cg.ST_N_SOG_ROP)
                            return
                        else:
                            self.log.info("Скидка вне таблицы (Прайс), но РОП уже согласовал.")
                    elif group_name == "Закупка":
                        if not self.big_data.get("galki", {}).get(self.cg.G_N_FINDIR, False):
                            self.s_galya(state_name=self.cg.ST_N_SOG_FINDIR)
                            return
                        else:
                            self.log.info("Скидка вне таблицы (Закупка), но Фин.директор уже согласовал.")
                    elif group_name == "Рецептура":
                        if not self.big_data.get("galki", {}).get(self.cg.G_N_TECHNOLOG, False):
                            self.s_galya(state_name=self.cg.ST_N_SOG_TECHNOLOG)
                            return
                        else:
                            self.log.info("Скидка вне таблицы (Рецептура), но Технолог уже согласовал.")
                    else:
                        self.log.info(f"Группа '{group_name}' скидка вне таблицы, нет отдельной логики.")
                    
                    continue

                # Если дошли сюда, значит у данной группы:
                # - нет нулевой цены
                # - нет несоответствия цены
                # - нет проблем со скидкой
                self.log.info(f"Группа '{group_name}' проблем не содержит. Продолжаем...")

            # Конец цикла for groups
            self.log.info("Все присутствующие группы проверены, проблем не найдено. Переводим счёт в 'Согласован'.")
            self.s_galya(state_name=self.cg.ST_N_GOOD)



        # Статус: "Цены Технолог"
        elif state_name == self.cg.ST_N_PRC_TECHNOLOG:
            if self.s_galka_check(self.cg.G_N_TECHNOLOG):
                self.s_in_work()

        # Статус: "Цены Фин.директор"
        elif state_name == self.cg.ST_N_PRC_FINDIR:
            if self.s_galka_check(self.cg.G_N_FINDIR):
                self.s_in_work()

        # Статус: "На согласование Фин.директор"
        elif state_name == self.cg.ST_N_SOG_FINDIR:
            if self.s_galka_check(self.cg.G_N_FINDIR):
                self.s_in_work()

        # Статус: "На согласование РОП"
        elif state_name == self.cg.ST_N_SOG_ROP:
            if self.s_galka_check(self.cg.G_N_ROP):
                self.s_in_work()

        # Статус: "На согласование Технолог"
        elif state_name == self.cg.ST_N_SOG_TECHNOLOG:
            if self.s_galka_check(self.cg.G_N_TECHNOLOG):
                self.s_in_work()

        # Статус: "Согласован"
        elif state_name == self.cg.ST_N_GOOD:
            changes_list = self.big_data.get("changes_list", [])
            # Если изменилась сумма или позиции — возвращаем на согласование менеджеру
            if 'sum' in changes_list or 'positions' in changes_list:
                self.s_galya(
                    state_name=self.cg.ST_N_SOG_MANAGER,
                    galks=[
                        self.cg.G_N_ROP,
                        self.cg.G_N_FINDIR,
                        self.cg.G_N_MANAGER,
                        self.cg.G_N_TECHNOLOG
                    ]
                )

    # ------------------------------------------------------------------------------
    # Ниже — методы вспомогательные (с префиксом s_)
    # ------------------------------------------------------------------------------
    
    def s_in_work(self):
        """s_in_work: Устанавливает статус 'В работе'."""
        self.s_galya(state_name=self.cg.ST_N_IN_WORK)

    def s_galka_check(self, galka_name):
        """Проверяет, была ли установлена галочка."""
        changes_list = self.big_data.get("changes_list", [])
        galki = self.big_data.get("galki", {})

        # Если галка действительно установлена (и есть в списке изменений)
        if galka_name in changes_list and galki.get(galka_name) is True:
            if self.s_face_controll(galka=galka_name):
                self.log.info(f"Галочка '{galka_name}' установлена пользователем.")
                return True
        
        # Если галка не установлена (galki[galka_name] == False), ждём
        if not galki.get(galka_name, False):
            self.log.info(f'Галочка "{galka_name}" не установлена, обработка не требуется.')
        else:
            # Иначе — сбрасываем галку (старая логика)
            self.s_galya(galks=[galka_name])  
        
        self.log.info(f"Галочка '{galka_name}' не установлена.")
        return False
    
    # ----------------------------------------------------------------------
    #      Две версии s_face_controll
    # ----------------------------------------------------------------------

    def s_face_controll(self, galka):
        """
        (1) s_face_controll (Заглушка)
        Возвращает True — т.е. всегда позволяет проставлять галку.
        """
        return True

    # def s_face_controll(self, galka):
    #     """
    #     (2) Реальная проверка прав пользователя — закомментированная версия.
    #     Если нужно подключить, раскомментируйте эту функцию
    #     (и закомментируйте заглушку).
    #     """
    #     changed_user = self.big_data.get("changed_user", None)
    #
    #     # Соответствие между именами галок в коде и на сервере
    #     galka_mapping = {
    #         self.cg.G_N_ROP: "ROP",
    #         self.cg.G_N_FINDIR: "Purchaseman",
    #         self.cg.G_N_TECHNOLOG: "Techman",
    #         self.cg.G_N_MANAGER: "Manager"
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
        """
        s_galya:
        Устанавливает статус счёта (state_name) и/или сбрасывает указанные галочки (galks).
        """
        self.log.info(f"Метод s_galya: state_name={state_name}, galks={galks}")

        data = {}
        states_data = self.big_data.get("states_data", [])
        invoiceout_id = self.big_data.get("invoiceout_id")

        # Если надо поменять статус
        if state_name is not None:
            state_id = None
            for st in states_data:
                if st['name'] == state_name:
                    state_id = st['id']
                    break
            if state_id is None:
                self.log.error(f"Статус '{state_name}' не найден среди доступных.")
                return
            data["state"] = {
                "meta": {
                    "href": f"https://api.moysklad.ru/api/remap/1.2/entity/invoiceout/metadata/states/{state_id}",
                    "metadataHref": "https://api.moysklad.ru/api/remap/1.2/entity/invoiceout/metadata",
                    "type": "state",
                    "mediaType": "application/json"
                }
            }
        
        # Если надо сбросить галочки
        if galks is not None and isinstance(galks, list):
            shab = {
                "meta": {
                    "href": "https://api.moysklad.ru/api/remap/1.2/entity/invoiceout/metadata/attributes/",
                    "type": "attributemetadata",
                    "mediaType": "application/json"
                },
                "id": "",
                "name": "",
                "type": "boolean",
                "value": False
            }
            attributes = []
            for galka_name in galks:
                attr_id = self.cg.ATTR_ID.get(galka_name)
                if attr_id:
                    one = deepcopy(shab)
                    one["meta"]["href"] += attr_id
                    one["id"] = attr_id
                    one["name"] = galka_name
                    one["value"] = False
                    attributes.append(one)
                else:
                    self.log.warning(f"Галочка '{galka_name}' не найдена в self.cg.ATTR_ID.")
            if attributes:
                data["attributes"] = attributes

        if not data:
            self.log.info("Нечего менять (state_name и galks оба None или пусты).")
            return

        # Отправляем PUT-запрос в МойСклад
        url = self.ms_api.meta_assembler(
            object_type='invoiceout',
            odject_id=invoiceout_id,
            href=True
        )
        output = self.ms_api.put(url=url, data=data)
        self.log.info(f"Обновление счёта в МойСклад: {output}")

        if state_name is not None:
            self.log.info(f"Статус переведён на '{state_name}'.")
        if galks is not None:
            self.log.info(f"Сброшены галочки: {galks}.")
