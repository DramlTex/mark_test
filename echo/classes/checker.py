import config
from copy import deepcopy
from jmespath import search as rip

class Checker:
    def __init__(self, event, ms_api):
        self.event = event
        self.ms_api = ms_api
        self.log = None
        self.event_dir = None
        self.event_dir_jsons = None
        self.cg = config
        self.invoiceout = None
        self.big_data = {
            "invoiceout_id": None,
            "changed_user": None,
            "changes_list": [],
            "галки": [],
            "state_id": None,
            "state_name": None,
            "states_data": [],
            "скидка_агента": 0,                   # Скидка контрагента
            "табличная_скидка": 0,                  # Скидка по таблице скидок
            "summa": 0.0,                         # Общая сумма счёта
            "total": {
                "нулевая_цена": False,            # Есть ли в счёте нулевые цены
                "больше_скидки_агента": False,    # Есть ли несоотвествие скидке контрагента
                "несоответсвие_цене_со_скидкой": False, # Есть ли в счёте несоотвествие "Цена со скидкой"
                "скидка_больше_табличной": False, # Есть ли несоотвествие таблице скидок
                "скидка_больше_10%": False,        # Есть ли скидка больше 10
            },
            "группы_товаров": {
                "Прайс": {
                    "нулевая_цена": False,
                    "скидка_больше_10%": False,
                    "несоответсвие_цене_со_скидкой": False,
                    "скидка_больше_табличной": False,
                    "больше_скидки_агента": False,
                    "максимальная_скидка": 0,
                    "discounts":  {0}
                },
                "Рецептура": {
                    "нулевая_цена": False,
                    "скидка_больше_10%": False,
                    "несоответсвие_цене_со_скидкой": False,
                    "скидка_больше_табличной": False,
                    "больше_скидки_агента": False,
                    "максимальная_скидка": 0,
                    "discounts":  {0}
                },
                "Закупка": {
                    "нулевая_цена": False,
                    "скидка_больше_10%": False,
                    "несоответсвие_цене_со_скидкой": False,
                    "скидка_больше_табличной": False,
                    "больше_скидки_агента": False,
                    "максимальная_скидка": 0,
                    "discounts":  {0}
                },
                "Акция": {
                    "нулевая_цена": False,
                    "скидка_больше_10%": False,
                    "несоответсвие_цене_со_скидкой": False,
                    "скидка_больше_табличной": False,
                    "больше_скидки_агента": False,
                    "максимальная_скидка": 0,
                    "discounts":  {0}
                },
                "Остальное": False
            }
        }
        
    def process_invoice(self):
        self.log.info("Запущен метод process_invoice (Checker).")
        # 1) Проверяем целостность события
        if not self.s_event_check():
            return
        # 2) Сохраняем базовые данные из event
        self.big_data["invoiceout_id"] = self.event["entity"]["meta"]["href"][-36:]
        self.big_data["changed_user"] = self.event['uid']
        self.big_data["changes_list"] = list(self.event.get('diff', {}).keys())
        self.log.info(f"ID счёта: {self.big_data['invoiceout_id']}")
        self.log.info(f"UID пользователя, сделавшего изменения: {self.big_data['changed_user']}")
        self.log.info(f"Изменённые поля: {self.big_data['changes_list']}\n")
        # 3) Получаем счёт
        self.log.info("Получаем счёт с товарами и агентом...")
        self.invoiceout = self.ms_api.get_invoiceout(
            inv_id=self.big_data["invoiceout_id"],
            expand="positions.assortment,agent"
        )
        self.ms_api.save_to_json(
            filename=f"{self.event_dir_jsons}/invoiceout.json",
            data=self.invoiceout
            )
        self.s_galki_checker()      # Проверяем галки
        self.s_check_state()        # Проверяем статус
        # Скидка контрагента
        self.big_data["скидка_агента"] = self.s_agent_discount_check()
        self.log.info(f"Скидка контрагента: {self.big_data['скидка_агента']}%\n")
        # 4) Анализ позиций по группам
        self.s_tovaroved()
        # 5) Сохраняем все данные big_data в JSON (если нужно)
        self.ms_api.save_to_json(
            filename=f"{self.event_dir_jsons}/big_data.json",
            data=self.big_data
            )
        self.log.info(f"Все итоговые данные сохранены в {self.event_dir_jsons}/big_data.json")
        # 6) Возвращаем self.big_data
        self.log.info("Обработка счёта (process_invoice) завершена.\n")
        return self.big_data

# ----------------------------------------------------------------------
# Подчинёные методы с префиксом s
# ----------------------------------------------------------------------

    def s_event_check(self):
        href = rip('entity.meta.href', self.event)
        diff = rip('diff', self.event)
        event_type = rip('eventType', self.event)
        if href and diff and event_type:
            return True
        self.log.error("Событие содержит не все нужные поля: href/diff/eventType.")
        return False
    
    def s_galki_checker(self):
        attributes = self.invoiceout.get('attributes', [])
        galki = self.big_data["галки"]
        for att in attributes:
            if att['value']:
                if att['name'] == self.cg.G_N_ROP:
                    galki.append(self.cg.G_N_ROP)
                elif att['name'] == self.cg.G_N_FINDIR:
                    galki.append(self.cg.G_N_FINDIR)
                elif att['name'] == self.cg.G_N_MANAGER:
                    galki.append(self.cg.G_N_MANAGER)
                elif att['name'] == self.cg.G_N_TECHNOLOG:
                    galki.append(self.cg.G_N_TECHNOLOG)
        self.log.info(f"Состояние галок: {galki}\n")

    def s_check_state(self):
        self.log.info("Запущен метод s_check_state (Checker).")
        self.fs_status_geter()
        state_id = self.invoiceout['state']['meta']['href'][-36:]
        self.big_data["state_id"] = state_id
        for st_name, st_id in self.big_data["states_data"].items():
            if st_id == state_id:
                self.big_data["state_name"] = st_name
                break
        self.log.info(f"Текущий статус: {self.big_data['state_name']} "
                      f"(ID: {self.big_data['state_id']})")
        self.log.info("Конец работы метода s_check_state\n")

    def s_agent_discount_check(self):
        self.log.info("Запущен метод s_agent_discount_check (Checker).")
        invoiceout = self.invoiceout
        agent = invoiceout.get('agent', {})
        attrs = agent.get('attributes', [])
        for att in attrs:
            if att['name'] == 'Скидка':
                raw_value = str(att['value']).strip()
                raw_value = raw_value.rstrip('%')
                try:
                    return int(raw_value)
                except ValueError:
                    pass
        return 0
    
    def s_tovaroved(self):
        self.log.info("Запущен метод s_tovaroved")
        summa = 0
        groups_data = self.big_data["группы_товаров"]
        for position in self.invoiceout["positions"]["rows"]:
            path_name = rip("assortment.pathName", position)
            tovar_name = position["assortment"]["name"]
            tovar_id = position["assortment"]["id"]
            self.log.info(f"Проверяю товар {tovar_name}, id: {tovar_id}, группа: {path_name}")
            summa += (position['price'] / 100) * position['quantity']
            # Узнаём группу товара
            if path_name not in ("Прайс", "Рецептура", "Закупка", "Акция"):
                groups_data["Остальное"] = True
                continue
            # Проверка: цена = 0
            if position['price'] == 0:
                groups_data[path_name]["нулевая_цена"] = True
                self.big_data["total"]["нулевая_цена"] = True
                self.log.warning("У товара нулевая_цена")
            # Проверка: цена не соотвествует "Цена со скидкой"
            if self.ts_price_for_sale_check(tovar=position):
                groups_data[path_name]["несоответсвие_цене_со_скидкой"] = True
                if path_name != "Рецептура":
                    self.big_data["total"]["несоответсвие_цене_со_скидкой"] = True
                self.log.warning('Цена не соотвествует "Цена со скидкой"')
            # Кидаем скидку в множество скидок
            groups_data[path_name]["discounts"].add(position["discount"])
        # Общая сумма заказа
        self.big_data["summa"] = summa
        table_discount = self.ts_get_normal_discount(summa)
        self.log.info(f"Табличная скидка: {table_discount}")
        self.big_data["табличная_скидка"] = table_discount
        # Анализ по группам
        for group_name, group_data in groups_data.items():
            if group_name == "Остальное":
                continue
            group_data["максимальная_скидка"] = float(max(group_data["discounts"]))
            if group_data["максимальная_скидка"] > self.big_data["скидка_агента"]:
                group_data["больше_скидки_агента"] = True
                self.big_data["total"]["больше_скидки_агента"] = True
            if group_data["максимальная_скидка"] > self.big_data["табличная_скидка"]:
                group_data["скидка_больше_табличной"] = True
                self.big_data["total"]["скидка_больше_табличной"] = True
            if group_data["максимальная_скидка"] > 10:
                group_data["скидка_больше_10%"] = True
                self.big_data["total"]["скидка_больше_10%"] = True
            group_data.pop("discounts")

#---------------------------------------------------
# Методы с прифксом ts - подичённые методу tovaroved
#---------------------------------------------------
    def ts_price_for_sale_check(self, tovar):
        """Проверяет соотвестие цены товара с "Цена со скидкой",
        возвращает True в случае несоотвествия"""
        self.log.info(f"Запущен метод ts_price_for_sale_check, цена товара: {tovar['price']}")
        sale_prices = rip("assortment.salePrices", tovar)
        if not sale_prices:
            self.log.error("В товаре отсутствует salePrices")
            return True
        price_standart = None
        for sale_price in sale_prices:
            if sale_price['priceType']['name'] == "Цена со скидкой":
                price_standart = sale_price['value']
                self.log.info(f"Цена со скидкой: {price_standart}")
                break
        if price_standart is None:
            self.log.error('В товаре отсутствует "Цена со скидкой"')
            return True
        if tovar["price"] != price_standart:
            return True
        
    def ts_get_normal_discount(self, summa):
        """Возвращает максимально разрешённую скидку на основе суммы"""
        if summa > 1000000:
            return 10
        else:
            for disc_info in self.cg.DISCOUNT_TABLE:
                if disc_info['min-sum'] <= summa <= disc_info['max-sum']:
                    return disc_info['discount']

# ----------------------------------------------------------------------
# Fucking slave методы
# ----------------------------------------------------------------------

    def fs_status_geter(self):
        metadata = self.ms_api.get(url=self.invoiceout['meta']['metadataHref'])
        self.log.info(metadata)
        big_states = metadata["states"]
        states_data = {s["name"]: s["id"] for s in big_states}
        self.big_data["states_data"] = states_data
        self.ms_api.save_to_json(
            filename=f"{self.event_dir_jsons}/small_state.json",
            data=states_data
            )