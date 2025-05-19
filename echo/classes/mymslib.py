import sys
import json
import base64
import requests
from jmespath import search as rip

def get_logger(log_name, logger_name, term=False):
    """Функция возвращает логгер"""
    import logging
    from logging.handlers import RotatingFileHandler
    import sys
    
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)
    
    if not logger.hasHandlers():
        # Файловый обработчик
        file_handler = RotatingFileHandler(
            log_name,
            mode='a',
            maxBytes=2 * 1024 * 1024,
            backupCount=5,
            encoding='utf-8',
            delay=True
        )
        file_handler.setLevel(logging.DEBUG)

        formatter = logging.Formatter(
            fmt="%(asctime)s [%(name)s] {Функция: %(funcName)s} (Line: %(lineno)d) | %(levelname)s %(message)s",
            datefmt='%Y/%m/%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        # Если включен вывод в терминал
        if term:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.DEBUG)
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)

    return logger


class APIClient:

    def __init__(self, us, pas, user_agent="OOO TechCenter", log=None):
        """
        Инициализация клиента с заданными данными.
        """
        self.username = us
        self.password = pas
        self.base_url = "https://api.moysklad.ru/api/remap/1.2/"
        self.user_agent = user_agent
        self.log = log 
        self.headers = self.get_headers()
        self._test_headers()


    def save_to_json(self, filename, data):
        """Сохраняет данные в json"""
        with open(filename, 'w', encoding='utf-8') as json_file:
            json.dump(data, json_file, ensure_ascii=False, indent=4)


    def get_headers(self):
        """Генерация заголовков для авторизации."""
        
        credentials = f"{self.username}:{self.password}"
        encoded_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')

        return {
            "Accept-Encoding": "gzip",
            "Content-Type": "application/json",
            "User-Agent": self.user_agent,
            "Authorization": f"Basic {encoded_credentials}"
        }


    def _test_headers(self):
        """Проверяет что заголовок действеннен"""
        r = requests.get(url="https://api.moysklad.ru/api/remap/1.2/entity/assortment?limit=1",
                         headers=self.headers)
        if r.status_code != 200:
            raise ValueError(f"Ошибка при проверке заголовка: {r.status_code}")


    def zapros(self, method, url, data=None, cnt=False):
        """Выполнение HTTP-запроса."""
        response = requests.request(method, url, headers=self.headers, json=data)

        if response.status_code == 200:
            if cnt:
                return response.content
            return response.json()
        else:
            raise ValueError(f"Ошибка HTTP: {response.status_code}. {response.text}")


    def price_assembler(self, data, name=None, prise_id=None, rip_pack=None):
        """Находит конкретную цену"""
        if name:
            for price in data:
                if price["priceType"]["name"] == name:
                    if rip_pack:
                        return self.ripper(data=price,
                                           rip_pack=rip_pack)
                    return price
        if prise_id:
            for price in data:
                if price["priceType"]["name"] == prise_id:
                    if rip_pack:
                        return self.ripper(data=price,
                                           rip_pack=rip_pack)
                    return price

    def meta_assembler(self, object_type, odject_id, href=False):
        """Собирает мету"""

        report_mass = []
        entity_mass = ['invoiceout', 'productfolder']

        if object_type in entity_mass:
            super_type = "entity"
        elif object_type in report_mass:
            super_type = "report"
        else:
            self.log(f"не смог определить к чему относится данный тип: {object_type}")
            sys.exit(1)

        if href:
            return f"{self.base_url}{super_type}/{object_type}/{odject_id}"

        meta = {
            "href": f"{self.base_url}{super_type}/{object_type}/{odject_id}",
            "metadataHref": f"{self.base_url}{super_type}/{object_type}/metadata",
            "type": object_type,
            "mediaType": "application/json",
            "uuidHref": f"https://online.moysklad.ru/app/#{object_type}/edit?id={odject_id}"
        }

        return meta

    def ripper(self, data, rip_pack):
        """JSON потрошитель."""

        if rip_pack == None:
            return data

        result = dict()

        for key, value in rip_pack.items():
            result[key] = rip(value, data)
        return result


    def get(self, url, cnt=False):
        """Метод для GET-запросов"""

        r = self.zapros(method="GET", url=url, cnt=cnt)

        return r


    def put(self, url, data):
        """Метод для GET-запросов"""

        r = self.zapros(method="PUT", url=url, data=data)

        return r


    def post(self, url, data):
        """Метод для GET-запросов"""

        r = self.zapros(method="POST", url=url, data=data)

        return r


    def mass_zapros(self, url, rip_pack=None):
        """Массово получает объекты."""

        result = list()

        while url:
            r = self.get(url=url)

            url = rip('meta.nextHref', r)

            rows = r['rows']

            if rip_pack:
                for row in rows:
                    nuw_rows = self.ripper(data=row, rip_pack=rip_pack)
                    result.append(nuw_rows)
            else:
                result.extend(rows)

        return result


    def get_invoiceout(self, inv_id=None, rip_pack=None, expand=None):
        """Получает Счёт покупателя"""
            
        url = self.base_url + "entity/invoiceout"
        if inv_id:
            url = f"{url}/{inv_id}"
        if expand:
            url = f"{url}?expand={expand}"
            
        if inv_id:
            return self.ripper(data=self.get(url=url), rip_pack=rip_pack)
        else:
            result = self.mass_zapros(url=url, rip_pack=rip_pack)

        return result


    def get_assortment(self, rip_pack=None):
        """Получает Ассортимент"""

        url = self.base_url + "entity/assortment"

        result = self.mass_zapros(url=url, rip_pack=rip_pack)

        return result


    def post_product(self, data):
        """Создаёт товар"""

        url = self.base_url + "entity/product"
        r = self.post(url, data)
        return r


    def post_customerorder(self, data):
        """Создаёт товар"""

        url = self.base_url + "entity/customerorder"
        r = self.post(url, data)
        return r