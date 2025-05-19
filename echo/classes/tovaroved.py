from jmespath import search as rip

def tovaroved(self):
    """
    Общий метод, который за один проход по позициям:
    1. Считает сумму без скидок (self.summa)
    2. Определяет группу товаров (self.assort_group)
    3. Проверяет, что цена позиции соответствует "Цене со скидкой" (self.price_matching)
       и заодно смотрит, нет ли нулевой цены (self.null_price)
    4. Запоминает максимальную скидку (max_disc), чтобы потом сравнить с "нормальной" из таблицы
    5. Проверяет скидку относительно скидки контрагента (self.discount_matching)
       и формирует флаг (self.discount_more_10), если скидка > 10
    6. После цикла сверяется с таблицей скидок (self.normal_discount).
    """

    self.log.info("Запущен метод tovaroved")
    
    # Будем искать **максимальную** скидку среди всех позиций
    max_disc = 0

    # Одним циклом бежим по всем позициям
    for position in self.invoiceout['positions']['rows']:
        # 1. Считаем сумму (без учёта скидки документа, просто price * quantity)
        position_sum = (position['price'] / 100) * position['quantity']
        self.summa += position_sum

        # 2. Определяем группу товара (pathName)
        path_name = rip("assortment.pathName", position)
        if path_name == "Прайс":
            self.assort_group['Прайс'] = True
        elif path_name == "Рецептура":
            self.assort_group['Рецептура'] = True
        elif path_name == "Закупка":
            self.assort_group['Закупка'] = True
        else:
            self.assort_group['Остальное'] = True

        # 3. Проверяем "цену со скидкой"
        sale_prices = rip("assortment.salePrices", position)
        if not sale_prices:
            self.log.error("В товаре отсутствуют salePrices")
            self.price_matching = False
        else:
            # Ищем "Цена со скидкой"
            price_standart = None
            for sale_price in sale_prices:
                if sale_price['priceType']['name'] == "Цена со скидкой":
                    price_standart = sale_price['value'] / 100
                    break
            if price_standart is None:
                self.log.error('В товаре отсутствует "Цена со скидкой"')
                self.price_matching = False
            else:
                # Сравниваем
                if position['price'] == 0:
                    self.null_price = True
                    self.price_matching = False
                elif (position['price'] / 100) != price_standart:
                    self.price_matching = False

        # 4. Проверяем скидки (discount)
        if 'discount' in position:
            disc = position['discount']
            # Сохраняем максимум
            if disc > max_disc:
                max_disc = disc

            # Если контрагент имеет скидку, и discount в позиции её превышает
            if self.agent_discount and disc > self.agent_discount:
                self.discount_matching = False

    #  - Дополнительно отметим discount_more_10, если max_disc > 10:
    if max_disc > 10:
        self.discount_more_10 = True

    # 6. Проверка на допустимую скидку по таблице (normal_discount).
    #    Для этого нужно знать self.summa.
    normal_discount = 10  # По умолчанию (для сумм свыше 1 000 000)
    if self.summa <= 1000000:
        for disc_info in self.cg.DISCOUNT_TABLE:
            if disc_info['min-sum'] <= self.summa <= disc_info['max-sum']:
                normal_discount = disc_info['discount']
                break

    self.log.info(f"Допустимая скидка по таблице: {normal_discount}%")

    # Если максимальная скидка среди позиций (max_disc) > normal_discount,
    # значит, скидка в счёте "не вписывается" в таблицу.
    if max_disc > normal_discount:
        self.log.info(f'Максимальная скидка: {max_disc}')
        self.normal_discount = False

    # Логи
    self.log.info(f'Сумма счёта без учёта скидок: {self.summa}')
    self.log.info(f"Группа товаров: {self.assort_group}")
    self.log.info(f"Товары с ценой 0: {self.null_price}")
    self.log.info(f'Совпадение цен с "Ценой со скидкой": {self.price_matching}')
    self.log.info(f'Соответствие скидки счёта скидке из таблицы (normal_discount): {self.normal_discount}')
    self.log.info(f'Соответствие скидки счёта скидке контрагента: {self.discount_matching}')
    self.log.info(f'Есть скидка > 10%: {self.discount_more_10}')
    self.log.info("Конец работы метода tovaroved\n")
