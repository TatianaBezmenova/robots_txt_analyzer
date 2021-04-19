import datetime
from yarl import URL
import json
from json.decoder import JSONDecodeError
from typing import Optional, Dict, Type, Tuple

import requests
from dataclasses import dataclass

"""Задача: У многих сайтов есть специальный файл robots.txt Задача этого файла донести до "поисковых" роботов (
программ, которые шерстят интернет и запоминают его состояние) указать, какие страницы можно запоминать, а какие нет. 

Пример:
Disallow: /search
Allow: /search/about
Allow: /search/static
Allow: /search/howsearchworks

В данном случае инструкция Allow указывает на разрешенную для "индексации" страницу, а Disallow - на запрещенную. 
Остальные инструкции можно игнорировать. 

Необходимо написать класс RobotsTxtAnalyzer, задачка которого состоит в следующием. Запросить файл robots.txt у 
указанного ресурса (например ресурс - google.com -> файл https://google.com/robots.txt) Прочитать содержимое файла, 
и составить статистику - количество разрешающих и запрещающих инсрукций. Так же стоит получить информацию из 
заголовков ответа, когда редактировался данный файл (заголовок ответа Last-Modified). Заголовка может не быть. Тогда 
оставить поле пустым. При выходе из програмы обновленные данные сохранить в тот же файл. 

Полученную информацию записать в JSON-файл, указанный пользователем.
Важно чтобы в одном JSON-файле можно было хранить статистику для нескольких файлов.
Как вариант - для каждого ресурса хранить информацию о его статистике.

Доп задачи: - Если указанный ресурс ранее запрашивался, не обновлять статистику, если его актуальное время изменения 
не изменилось с предыдущего раза Для этого запрос все таки придется выполнить (Last-Modified). - Для 
"предварительного" запроса не скачивать содержимое файла, нас интересуют только заголовки (HEAD или OPTIONS) - 
Реализовать работу класса через контекстный менеджер (загрузка и сохранение данных статистики) """


class RobotsTxtNotFound(Exception):
    """
    Если у сайта отсутствует файл robots.txt
    """


@dataclass
class Stats:
    """
    Класс данных статистики ресурса - allow - количество разрешающих инстркций в файле - disallow - количество
    запрещающих инструкций инстркций в файле - last_modified - время последней модификации в формате unix-timestamp,
    может быть пустой (None) если ресурс не предоставляет такой информации
    """

    allow: int = 0
    disallow: int = 0
    last_modified: Optional[int] = None


class RobotsTxtAnalyser:
    """
    Класс логики анализа robots.txt
    """

    filename: str
    _resources_stats: Dict[str, Dict]

    def __init__(self, filename: str):
        self.filename = filename
        self._resources_stats = {}

    @staticmethod
    def prepare(resource: str) -> Tuple[str, str]:
        if not URL(resource).scheme:
            resource = str(URL.build(scheme="https", host=resource))
        url_robots_txt = str(URL(resource).with_path("/robots.txt"))
        return resource, url_robots_txt

    @staticmethod
    def parse_last_modified_from_string(date_string: str):
        return datetime.datetime.strptime(date_string, "%a, %d %b %Y %H:%M:%S %Z")

    def parse_last_modified_from_float(self, resource: str):
        return datetime.datetime.fromtimestamp(self._resources_stats[resource]["last_modified"])

    @staticmethod
    def fetch(url_robots_txt: str) -> str:
        """
        Получить robots.txt у ресурса, вернуть его содержимое
        """
        return requests.get(url_robots_txt).text

    @staticmethod
    def collect_stats(content: str) -> Stats:
        """
        Обоработать содержимое файла robots.txt, составить статистику
         - content - содержимое robots.txt
        """
        stats = Stats()
        stats.allow = content.count("Allow:")
        stats.disallow = content.count("Disallow:")
        return stats

    @staticmethod
    def inspect(url_robots_txt: str) -> Optional[datetime.datetime]:
        response = requests.head(url_robots_txt)
        if response.status_code == 404:
            raise RobotsTxtNotFound
        last_modified = response.headers.get("Last-Modified")
        if last_modified is None:
            return None
        return RobotsTxtAnalyser.parse_last_modified_from_string(last_modified)

    def analyze(self, resource: str):
        """
        Провести анализ ресурса, и обновить информацию по нему, если она уже имелась
         - resourse - имя домена, например google.com
        """
        resource, url_robots_txt = RobotsTxtAnalyser.prepare(resource)
        last_modified = self.inspect(url_robots_txt)

        if resource in self._resources_stats and self.parse_last_modified_from_float(resource) > last_modified:
            return
        stats = self.collect_stats(self.fetch(url_robots_txt))
        if last_modified:
            stats.last_modified = last_modified.timestamp()

        self._resources_stats[resource] = stats.__dict__

    def load(self):
        """
        Загрузить предыдущие данные анализа ресурсов из файла
        """
        with open(self.filename, 'r') as f:
            try:
                self._resources_stats = json.load(f)
            except JSONDecodeError:
                self._resources_stats = {}

    def save(self):
        """
        Сохранить обновленные данные анализа ресурсов в файл
        """
        with open(self.filename, 'w') as f:
            f.write(json.dumps(self._resources_stats))

    def __enter__(self) -> "RobotsTxtAnalyser":
        self.load()
        return self

    def __exit__(self, exc_type: Type[Exception] = None, exc_value: Exception = None, traceback=None):
        self.save()


if __name__ == "__main__":
    filename = input("Enter filename: ")
    resource = input("Enter resource: ")

    with RobotsTxtAnalyser(filename) as analyzer:
        analyzer.analyze(resource)
