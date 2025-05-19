import config
from copy import deepcopy
from jmespath import search as rip
from classes.tovaroved import tovaroved

class Event_worker:
    tovaroved = tovaroved
    def __init__(self, event, ms_api):
        """Инициализирует экземпляр Event_worker с данными о событии, 
        клиентом ms_api и логгером. Создаёт или определяет файл лога для данного события."""
        self.event = event      # Полный евент
        self.ms_api = ms_api    # Объект общения с МС
        self.log = None          # Лог
        self.event_dir = None
        self.event_dir_jsons = None
        self.cg = config
        
    def start(self):
        self.log.info("Запущен метод start")

        self.invoiceout_id = self.event["entity"]["meta"]["href"][-36:]
        self.log.info(f"id счёта: {self.invoiceout_id}")
        
        self.changed_user = self.event['uid']
        self.log.info(f"uid пользователя сделавшего изменения: {self.changed_user}")
    
        self.log.info("Получаем счёт с товарами и агентом...")
        self.invoiceout = self.ms_api.get_invoiceout(inv_id=self.invoiceout_id,
                                                     expand="positions.assortment,agent")
        
        self.ms_api.save_to_json(filename=f"{self.event_dir_jsons}/invoiceout.json",
                                 data=self.invoiceout)
        self.log.info(f"Счёт получен и сохранён в {self.event_dir_jsons}/invoiceout.json")
        
        self.changes_list = list(self.event.get('diff', {}).keys())
        self.log.info(f"Изменённые поля: {self.changes_list}\n")
        
        # Узнаём состояние галочек
        self.galki = {}
        self.galki_checker()
        
        # Узнаём статус
        self.state_id = None
        self.state_name = None
        self.states_data = list()
        self.check_state()
        
        # Скидка контрагента
        self.agent_discount = self.agent_discount_check()
        self.log.info(f"Скидка контрагенты: {self.agent_discount}%\n")
        
        self.summa = 0.0               # Сумма без учёта скидок
        # Группа товаров (Прайс/Рецептура/Закупка/Несколько/other)
        self.assort_group = {
            "Прайс": False,
            "Рецептура": False,
            "Закупка": False,
            "Остальное": False
            }      
        self.null_price = False        # Есть нулевые цены?
        self.price_matching = True     # Все позиции соответствуют "Цене со скидкой?
        self.discount_more_10 = False  # Есть ли скидка больше 10%?
        self.discount_matching = True  # Скидка меньше скидки контрагента (если есть)?
        self.normal_discount = True    # Скидки совпадают с позици скидок?

        self.tovaroved()


    def galki_checker(self):
        """Проверяет выставленные галки"""
        for att in self.invoiceout['attributes']:
            if att['name'] == self.cg.G_N_ROP:
                self.galki[self.cg.G_N_ROP] = att['value']
            if att['name'] == self.cg.G_N_FINDIR:
                self.galki[self.cg.G_N_FINDIR] = att['value']
            if att['name'] == self.cg.G_N_MANAGER:
                self.galki[self.cg.G_N_MANAGER] = att['value']
            if att['name'] == self.cg.G_N_TECHNOLOG:
                self.galki[self.cg.G_N_TECHNOLOG] = att['value']
        self.log.info(f"Состояние галок: {self.galki}\n")

    def check_state(self):
        """Получает статус"""
        self.log.info("Запущен метод check_state")
        
        big_stat_json = f"{self.event_dir_jsons}/big_state.json"
        small_stat_json = f"{self.event_dir_jsons}/small_state.json"
        
        rip_pack = {
            'states': 'states'
        }
        metadata = self.ms_api.get(url=self.invoiceout['meta']['metadataHref'])
        big_states = self.ms_api.ripper(data=metadata,
                            rip_pack=rip_pack)
        
        self.ms_api.save_to_json(filename=f"{big_stat_json}",
                                          data=big_states)
        self.log.info(f"Полные данные статусов сохранены в {big_stat_json}.")
        
        for state in big_states['states']:
            one = dict()
            one['name'] = state['name']
            one['id'] = state['id']
            self.states_data.append(one)
        
        self.ms_api.save_to_json(filename=f"{small_stat_json}",
                                 data=self.states_data)
        self.log.info(f"Краткие данные статусов сохранены в {small_stat_json}")

        self.state_id = self.invoiceout['state']['meta']['href'][-36:]
        self.log.info(f"ID статуса документа: {self.state_id}")
        for state_data in self.states_data:
            if state_data['id'] == self.state_id:
                self.state_name = state_data['name']
                self.log.info(f"Имя статуса: {self.state_name}")
        
        self.log.info(f"Конец работы метода check_state\n")
        

    def agent_discount_check(self):
        self.log.info("Запущен метод agent_discount_check")
        """Выявляет скидку контрагента (целое число).
        Значение может быть как '10%', так и '10'. 
        Возвращает int или None, если не найдено.
        """
        attrs = self.invoiceout.get('agent', {}).get('attributes', [])
        for att in attrs:
            if att['name'] == 'Скидка':
                raw_value = str(att['value']).strip()  # на всякий случай переводим в строку и убираем пробелы
                raw_value = raw_value.rstrip('%') # Если значение заканчивается на '%', убираем символ '%'
                self.log.info(f"Конец работы метода agent_discount_check. Возврат: {int(raw_value)}")
                return int(raw_value)
        self.log.info(f"Конец работы метода agent_discount_check. Возврат: 0")
        return 0


    def event_check(self):
        """Проверяет целостность события: наличие href, diff, eventType."""
        href = rip('entity.meta.href', self.event)
        diff = rip('diff', self.event)
        event_type = rip('eventType', self.event)
        if href and diff and event_type:
            return True
        self.log.error("Событие содержит не все должные поля.")
        return False


    def face_controll(self, galka):
        """Проверяет, может ли пользователь с данным uid и галкой внести изменения.
        Выполняет запрос к PHP-скрипту для проверки прав."""
        
        # # Соответствие между именами галок в коде и на сервере
        # galka_mapping = {
        #     self.cg.G_N_ROP: "ROP",
        #     self.cg.G_N_FINDIR: "Purchaseman",
        #     self.cg.G_N_TECHNOLOG: "Techman"
        # }
        
        # # Получаем имя галки для сервера
        # server_galka = galka_mapping.get(galka)
        
        # # Если галка не найдена в маппинге, считаем, что доступ запрещён
        # if not server_galka:
        #     self.log.warning(f"Неизвестная галка: {galka}")
        #     self.log.info(f"Неизвестная галка: {galka}")
        #     return False
        
        # # URL вашего PHP-скрипта
        # url = "http://85.193.91.150/Soglasovator/employees/mark_vizer.php"
        
        # # Данные для POST-запроса
        # data = {
        #     "uid": self.changed_user,  # uid пользователя
        #     "key": server_galka        # Галка для сервера (ROP, Purchaseman, Techman)
        # }
        
        # # Выполняем POST-запрос
        # response = self.ms_api.zapros("POST", url, data=data)
        
        # # Логируем ответ от сервера
        # self.log.info(f"Ответ от сервера для галки {server_galka}: {response}")
        
        # controll = response.get("result", False)
        # if controll == False:
        #     self.log.info(f"У пользователя {self.changed_user} нет прав на установку согласования")
        #     self.galya(state_name=galka)
        #     return False
        
        return True

    def galya(self, state_name=None, galks=None):
        """Устанавливает статус счёта и сбрасывает указанные галочки."""
        # Логируем передаваемые аргументы
        self.log.info(f"Переданные аргументы: state_name={state_name}, galks={galks}")
        
        ms_in_data = f"{self.event_dir_jsons}/ms_in_data.json"
        ms_out_data = f"{self.event_dir_jsons}/ms_out_data.json"

        # Если оба параметра None, ничего не делаем
        if state_name is None and galks is None:
            self.log.info("Параметры state_name и galks не переданы. Ничего не делаем.")
            return

        # Логируем начало работы функции
        self.log.info("Обращение к Мой Склад")

        # Если передан state_name, устанавливаем статус
        state_id = None
        if state_name is not None:
            for state in self.states_data:
                if state['name'] == state_name:
                    state_id = state['id']
                    break

            if state_id is None:
                self.log.error(f"Статус '{state_name}' не существует.")
                return

        # Подготовка данных для отправки
        data = {}

        # Если передан state_name, добавляем его в данные
        if state_name is not None:
            data["state"] = {
                "meta": {
                    "href": f"https://api.moysklad.ru/api/remap/1.2/entity/invoiceout/metadata/states/{state_id}",
                    "metadataHref": "https://api.moysklad.ru/api/remap/1.2/entity/invoiceout/metadata",
                    "type": "state",
                    "mediaType": "application/json"
                }
            }

        # Если передан galks, сбрасываем указанные галочки
        if galks is not None:
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
                if galka_name in self.cg.ATTR_ID:
                    attr_id = self.cg.ATTR_ID[galka_name]
                    one = deepcopy(shab)
                    one["meta"]["href"] += attr_id
                    one["name"] = galka_name
                    one["id"] = attr_id
                    attributes.append(one)
                else:
                    self.log.warning(f"Галочка '{galka_name}' не найдена в self.cg.ATTR_ID.")

            if attributes:
                data["attributes"] = attributes

        # Отправка данных
        url = self.ms_api.meta_assembler(object_type='invoiceout',
                                        odject_id=self.invoiceout_id,
                                        href=True)
        
        self.ms_api.save_to_json(filename=ms_in_data,
                                 data=data)
        self.log.info(f"Данные для отправления в Мой Склад сохранены в {ms_in_data}:")
        
        output = self.ms_api.put(url=url, data=data)
        
        self.ms_api.save_to_json(filename=ms_out_data,
                                 data=output)
        self.log.info(f"Ответ Моего Склада сохранён в {ms_out_data}:")

        # Логируем успешное выполнение
        if state_name is not None:
            self.log.info(f"Статус '{state_name}' установлен.")
        if galks is not None:
            self.log.info(f"Галочки {galks} сброшены.")
    
    def galka_check(self, galka_name):
        """Проверяет, была ли установлена галочка."""
        if galka_name in self.changes_list and self.galki[galka_name] == True:
            if self.face_controll(galka=galka_name):
                self.log.info(f"Галочка '{galka_name}' установлена.")
                return True
        if self.galki[galka_name] == False:
            self.log.info(f'Ждём установки галочки "{galka_name}", обработка не требуется.')
        else:
            self.galya(galks=[galka_name]) # Снимаем галку
        self.log.info(f"Галочка '{galka_name}' не установлена.")
        return False

    def in_work(self):
        self.galya(state_name=self.cg.ST_N_IN_WORK) 

    def problem_check(self):
        self.log.info("Запущен метод problem_check")
        # Если цена не соответсвует "Цена со скидкой" или
        # скидка контрагента 0 и скидка в счёте не соотвествует таблице скидок
        # или есть скидка больше 10%
        # или скидка больше скидки в контрагенте
        if self.price_matching == False:
            self.log.info('Цена позиции не соотвествует "Цена со скидкой')
            return True
        elif self.discount_matching == False:
            self.log.info('Скидка больше скидки контрагента')
            return True
        elif self.discount_more_10 == True:
            self.log.info('Есть скидка больше 10%')
            return True
        elif self.normal_discount == False:
            self.log.info('Скидки не совпадают с таблицей скидок')
            return True
        else:
            self.log.info('Проблем нет')
            return False


    def techonolog_check(self):
        self.log.info("Запущен метод techonolog_check")
        
        if self.assort_group["Рецептура"]:
            self.log.info('Найдены товары группы "Рецептура"')
            if self.galki[self.cg.G_N_TECHNOLOG] == False:
                self.galya(state_name=self.cg.ST_N_SOG_TECHNOLOG)
                return True


    def findir_check(self):
        self.log.info("Запущен метод findir_check")
        self.log.info(f"discount_matching: {self.discount_matching}")
        self.log.info(f"discount_more_10: {self.discount_more_10}")
        if self.galki[self.cg.G_N_FINDIR] == False:
            self.log.info('Галочка "Согласованно Фин.директором" не установленна')
            
            # Если есть товары из категории "Закупка"
            # Или скидка больше 10% и это не закрепленно в контраегнет
            if self.assort_group["Закупка"] == True:
                self.galya(state_name=self.cg.ST_N_SOG_FINDIR)
                return True
            elif self.discount_matching == True and self.discount_more_10 == True:
                self.galya(state_name=self.cg.ST_N_SOG_FINDIR)
                return True


    def rop_check(self):
        self.log.info("Запущен метод rop_check")
        self.log.info(f"discount_matching: {self.discount_matching}")
        self.log.info(f"normal_discount: {self.normal_discount}")
        if self.galki[self.cg.G_N_ROP] == False:
            self.log.info('Галочка "Согласованно РОП" не установленна')
            
            # Если есть товары из категории "Прайс"
            # И скидка не совпадает с таблицей и это не закрепленно в контраегнет
            if (self.assort_group["Прайс"] == True
                or self.discount_matching == True and self.normal_discount == False):
                
                self.galya(state_name=self.cg.ST_N_SOG_ROP)
                return True


    def event_manager(self):
        """Основной метод обработки события."""
        self.log.info("Запущен метод event_manager")

        # Дали битый евент? Отбой!
        if not self.event_check():
            return

        self.log.info(f'Обработка по статусу: "{self.state_name}".')
        # Статус: На согласование Менеджер
        if self.state_name == self.cg.ST_N_SOG_MANAGER:
            if self.galka_check(galka_name=self.cg.G_N_MANAGER):
                self.in_work()

        # Статус: В работе
        elif self.state_name == self.cg.ST_N_IN_WORK:
            # Если есть нулевая цена
            if self.null_price == True:
                if self.assort_group["Рецептура"] == True:
                    self.galya(state_name=self.cg.ST_N_PRC_TECHNOLOG)
                elif self.assort_group['Закупка'] == True:
                    self.galya(state_name=self.cg.ST_N_PRC_FINDIR)
                else:
                    self.log.info("Товары в счёте не относятся к нужным группам.")

            elif self.problem_check():
                if self.techonolog_check():
                    return
                if self.findir_check():
                    return
                if self.rop_check():
                    return
                else:
                    self.galya(state_name=self.cg.ST_N_GOOD) 
            else:
                self.galya(state_name=self.cg.ST_N_GOOD) 

        # Статус: Цены Технолог
        elif self.state_name == self.cg.ST_N_PRC_TECHNOLOG:
            if self.galka_check(galka_name=self.cg.G_N_TECHNOLOG):
                self.in_work() 

        # Статус: Цены Фин.директор
        elif self.state_name == self.cg.ST_N_PRC_FINDIR:
            if self.galka_check(galka_name=self.cg.G_N_FINDIR):
                self.in_work()

        # Статус: На согласование Фин.директор
        elif self.state_name == self.cg.ST_N_SOG_FINDIR:
            if self.galka_check(galka_name=self.cg.G_N_FINDIR):
                self.in_work()
        
        # Статус: На согласование РОП
        elif self.state_name == self.cg.ST_N_SOG_ROP:
            if self.galka_check(galka_name=self.cg.G_N_ROP):
                self.in_work()
        
        # Статус: На согласование Технолог
        elif self.state_name == self.cg.ST_N_SOG_TECHNOLOG:
            if self.galka_check(galka_name=self.cg.G_N_TECHNOLOG):
                self.in_work()
        
        # Статус: Согласован
        elif self.state_name == self.cg.ST_N_GOOD:
            # Изменилась сумма или позиции
            if 'sum' in self.changes_list or 'positions' in self.changes_list:
                self.galya(state_name=self.cg.ST_N_SOG_MANAGER,
                           galks=[
                                self.cg.G_N_ROP,
                                self.cg.G_N_FINDIR,
                                self.cg.G_N_MANAGER,
                                self.cg.G_N_TECHNOLOG
                           ])
        
