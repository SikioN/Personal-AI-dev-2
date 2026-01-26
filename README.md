#### Структура файловой системы:
- debug/ - Директория с ноутбуками/скриптами для отладки кода из каталога "src".
- experiments/ - Директория с реализациями проведённых экспериментов: дообучение/обучение моделей, подбор гиперпараметров модели и т.п. Каждый эксперимент в отдельной директории. Обязательно логирование в отдельном каталоге "logs" (для каждого каталога с экспериментом свой каталог с логами): пул гиперпарметров + полученные метрики.
- notebooks/ - Директория с переиспользуемыми ноутбуками: связанные с предобработкой датасетов, формированием баз данных и т.п.
- src/ - Директория с production-кодом проекта.
- tests/ - Директория с модульными/интеграционными тестами для кода из каталога "src".
- models/ - Директория с нейросетевыми моделями (используем DVC для версионирования и совместного использования)
- data/ - Директория с датасетами/базами данных (используем DVC для версионирования и совместного использования)
- docs/ - Директория с документацией проекта.

#### Структура веток:
- dev - Предназначена для реализации функционала разрабатываемой библиотеки. Для решения конкретной задачи в рамках "dev" нужно создать от неё отдельную ветку, реализовать решение и смёржить в dev и удалить ветку из репозитория. Названия данных веток имеет следующий формат: номер issue в gitlab с описание задачи (task#N).
- test - Предназначена для написания/запуска тестов по реализованному функционалу из ветки dev. На данной стадии выполняется проверка на соответствие логики программного кода заданным функциональным требованиям.
- master - Рабочая версия кода для демонстрации заказчику. ВНИМАНИЕ: в main можно только сливать изменения из ветки test. Делать комиты в ветку напрямую запрещено!
- exp - Предназначена для проведения экспериментов. Для решения конкретной задачи в рамках "exp" нужно создать от неё отдельную ветку, реализовать решение и (после review от лида) смёржить в "exp" и удалить ветку из репозитория. Для проведения эксперимента необходимо создать отдельную директорию в каталоге "experiments"; название директории должно быть в следующем формате: "суть_эксперимента (#N)". Эксперименты могут быть вложенными: есть директория с общим названием эксперимента, в рамках которого прооводится несколько атомарных исследований.
- task#N - Предназначеная для решения конкретной/атомарной задачи, проведения эксперимента, описанной в соответствующем issue на gitlab.

Пример работы с описанной структурой веток:

![alt text](https://github.com/zer0o0ne/Personal-AI/blob/dev/docs/branch_workflow.jpg)

##### Полезные материалы (структура ML-проекта):
* https://drive.google.com/file/d/1g0tzALqKygFTtzA-C5l5ZOdC9tKiUTzc/view?usp=sharing

##### Команда для деплоя контейнеров:
* docker build -t m.menschikov/agent_api:v2 .
* docker run -d -p 45678:4567 -v ./models:/app/models -it  --name m.menschikov.agent_api_cntrn --memory=32g --memory-swap=32g --cpuset-cpus=0-4 --gpus '"device=1"' m.menschikov/agent_api:v2

##### Команды для генерации документации:
* find . -type d -name __pycache__ -exec rm -r {} \+
* sphinx-apidoc -o ../docs/tmp/ .
* make html
* make latexpdf
* make singlehtml
* make clean

##### Команды для тестироваания
* pytest --cov=src --cov-report=html ...

pre-commit:
* https://pre-commit.com/#pre-commit-configyaml---repos
* https://www.laac.dev/blog/automating-convention-linting-formatting-python/

dvc tutorial:
* get-start - https://dvc.org/doc/start
* remote ssh-storage - https://dvc.org/doc/user-guide/data-management/remote-storage/ssh
* remote gdrive-storage - https://dvc.org/doc/user-guide/data-management/remote-storage/google-drive

pytest tutorial:
* https://realpython.com/pytest-python-testing/#parametrization-combining-tests


Построенные графы знаний:
1. (testdb) - golden-граф
    * vectorized nodes = 8
    * vectorized triplets = 4
2. (diaasq2) - build-грфа (c добавленным полем time)
    * vectorized nodes = 10
    * vectorized triplets = 6
3. (diaasq_gpt4omini) - build-граф (diaasq2 с добавленным полем name для realtions)
    * vectorized nodes = 11
    * vectorized triplets = 7
4. (diaasq_gigachat) - build-граф (diaasq2 с добавленным полем name для realtions)
    * vectorized nodes = 12
    * vectorized triplets = 8
5. (testdb_v2) -  testdb-граф, который был перестроен по обновлённому алгоритму (более строгий контроль за дубликатами вершин и связей)
    * vectorized nodes = 13
    * vectorized triplets = 9
    * graph-creation info: all/created_relations - 10355/10296; all/created_nodes - 20710/1434
6. (diaasq_gpt4omini_v2) -  diaasq_gpt4omini-граф, который был перестроен по обновлённому алгоритму (более строгий контроль за дубликатами вершин и связей)
    * vectorized nodes = 14
    * vectorized triplets = 10
    * graph-creation info: all/created_relations - 283268/72789; all/created_nodes - 566536/71254
7. (diaasq_gigachat_v2) -  diaasq_gigachat-граф, который был перестроен по обновлённому алгоритму (более строгий контроль за дубликатами вершин и связей)
    * vectorized nodes = 15
    * vectorized triplets = 11
    * graph-creation info: all/created_relations - 211542/50917; all/created_nodes - 423084/54051
