import json
from json.decoder import JSONDecodeError
from typing import Optional, Dict, Type

import requests
from dataclasses import dataclass

"""
Задача:
У многих сайтов есть специальный файл robots.txt
Задача этого файла донести до "поисковых" роботов (программ, которые шерстят интернет и запоминают его состояние) указать, какие страницы можно запоминать, а какие нет.

Пример:
Disallow: /search
Allow: /search/about
Allow: /search/static
Allow: /search/howsearchworks

В данном случае инструкция Allow указывает на разрешенную для "индексации" страницу, а Disallow - на запрещенную. Остальные инструкции можно игнорировать.

Необходимо написать дописать класс RobotsTxtAnalyzer, задачка которого состоит в следующием.
Запросить файл robots.txt у указанного ресурса (например ресурс - google.com -> файл https://google.com/robots.txt)
Прочитать содержимое файла, и составить статистику - количество разрешающих и запрещающих инсрукций.
Так же стоит получить информацию из заголовков ответа, когда редактировался данный файл (заголовок ответа Last-Modified). Заголовка может не быть. Тогда оставить поле пустым.
При выходе из програмы обновленные данные сохранить в тот же файл.

Полученную информацию записать в JSON-файл, указанный пользователем.
Важно чтобы в одном JSON-файле можно было хранить статистику для нескольких файлов.
Как вариант - для каждого ресурса хранить информацию о его статистике.


Доп задачи:
 - Если указанный ресурс ранее запрашивался, не обновлять статистику, если его актуальное время изменения не изменилось с предыдущего раза
   Для этого запрос все таки придется выполнить (Last-Modified). 
 - Для "предварительного" запроса не скачивать содержимое файла, нас интересуют только заголовки (HEAD или OPTIONS)
 - Реализовать работу класса через контекстный менеджер (загрузка и сохранение данных статистики)
"""


@dataclass
class Stats:
    """
    Класс данных статистики ресурса

     - allow - количество разрешающих инстркций в файле
     - disallow - количество запрещающих инструкций инстркций в файле
     - last_modified - время последней модификации в формате unix-timestamp, может быть пустой (None) если ресурс не предоставляет такой информации
        Для того чтобы конвертировать строчку с датой в этот формат можно воспользоватся следующим кодом 
        datetime.datetime.strptime("Mon, 11 Jan 2021 21:00:00 GMT", "%a, %d %b %Y %H:%M:%S %Z").timestamp()


    В класс можно добавить методы, если это необходимо
    """
    allow: int = 0
    disallow: int = 0
    last_modified: Optional[str] = None


class RobotsTxtAnalyser:
    """
    Класс логики анализа robots.txt

    Сигнатуру существующих методов менять не стоит, но можно добавить новые, если это необходимо
    """
    filename: str
    _resources_stats: Dict[str, Dict]

    def __init__(self, filename: str):
        self.filename = filename
        self.resources_stats = {}

    @property
    def resources_stats(self):
        return self._resources_stats

    @resources_stats.setter
    def resources_stats(self, value):
        self._resources_stats = value

    @staticmethod
    def prepare(resource: str) -> str:
        resource = resource.strip("/")
        if resource[:8] == "https://" or resource[:7] == "http://":
            return resource
        return f"https://{resource}"

    def fetch(self, resource: str) -> str:
        """
        Получить robots.txt у ресурса, вернуть его содержимое

         - resourse - имя домена, например google.com

        Обработать возможные ошибки:
         - Страница robots.txt не существует
        """
        return requests.get(f"{resource}/robots.txt").text

    def collect_stats(self, content: str) -> Stats:
        """
        Обоработать содержимое файла robots.txt, составить статистику

         - content - содержимое robots.txt (пример можно посмотреть https://google.com/robots.txt)
        """
        stats = Stats()
        stats.allow = content.count("Allow:")
        stats.disallow = content.count("Disallow:")
        return stats

    def analyze(self, resource: str):
        """
        Провести анализ ресурса, и обновить информацию по нему, если она уже имелась

         - resourse - имя домена, например google.com

        """
        resource = RobotsTxtAnalyser.prepare(resource)
        self.load()
        response = requests.get(f"{resource}/robots.txt")
        if response.status_code == 200:
            try:
                last_modified = response.headers["Last-Modified"]
            except KeyError:
                last_modified = ""
            if resource in self.resources_stats and last_modified == self.resources_stats[resource]["last_modified"]:
                return

            content = self.fetch(resource)
            stats = self.collect_stats(content)
            stats.last_modified = last_modified
            self.resources_stats[resource] = stats.__dict__

    def load(self):
        """
        Загрузить предыдущие данные анализа ресурсов из файла
        """
        with open(self.filename, 'r') as f:
            try:
                self.resources_stats = json.load(f)
            except JSONDecodeError:
                self.resources_stats = {}

    def save(self):
        """
        Сохранить обновленные данные анализа ресурсов в файл
        """
        with open(self.filename, 'w') as f:
            f.write(json.dumps(self.resources_stats))

    def __enter__(self) -> "RobotsTxtAnalyser":
        return self

    def __exit__(self, exc_type: Type[Exception] = None, exc_value: Exception = None, traceback=None):
        self.save()


if __name__ == "__main__":
    filename = input("Enter filename: ")
    resource = input("Enter resource: ")

    with RobotsTxtAnalyser(filename) as analyzer:
        analyzer.analyze(resource)
