### PROMPT IN ENGLISH ###

EN_THESISES_EXTRACTION_SYSTEM_PROMPT = \
'''
Objective: The main goal is to meticulously gather information from input [Text] and organize this data into a clear, structured knowledge graph.

Requirements for building a knowledge graph:
1. Entities must depict concepts, similar to Wikipedia nodes. Entities must not include verbs and any other words which described motion, properties and etc. All the entities must be the real world objects or abstract concept. Use a structured thesises format to capture data. For example, from [Text] "Albert Einstein, born in Germany, is known for developing the theory of relativity" [Extracted thesises] should be "Albert Einstein was born in Germany | ['Albert Einstein', 'Germany', 'birth']", "Albert Einstein developed Theory of Relativity | ['Albert Einstein', 'developing', 'Theory of Relativity'].".
2. Thesises MUST BE comprehension and consistent, so you can make them in form of sentense. You better make a much longer thesis than split it into two which inconsistent separately. For example, you better extract thesis "North exit from kitchen is blocked by door" than "kitchen has door" and "north exit is blocked by door" because without context of kitchen "north exit is blocked by door" can be related to every room at home.
3. You should extract only concrete knowledges, any assumptions must be described as hypothesis. For example, from [Text] "John have scored many points and potentially will be winner" [Extracted thesises] should be "John scored many points | ['John', 'scoring', 'point']", "John could be winner | ['John', 'winner']." and you should not extract "John will be winner | ['John', 'winner'].".
4. Remember that nodes must be an atomary units while thesis can be more complex and long.
5. Do not miss important information. If [Text] is "book involves story about knight, who needs to kill a dragon", thesises should be "book involves knight", "knight needs to kill dragon".
6. Several thesises can be extracted, that contain information about the same node. For example "kitchen contains apple", "kitchen contains table", "apple is on table". Do not miss this type of connections.
7. Do not use "none" as one of the entities.

[Extracted thesises] should be returned in the following format:
thesis_1 | [list of entites for thesis_1];
thesis_2 | [list of entites for thesis_2];
...
thesis_n | [list of entites for thesis_n].
'''

# As a response generate only extracted thesises in the format, described above and do not include additional explanations of the obtained result.

EN_THESISES_EXTRACTION_USER_PROMPT = \
'''
[Text]:
{text}
'''

EN_THESISES_EXTRACTION_ASSISTANT_PROMPT = \
'''
[Extracted thesises]:
'''

### PROMPT IN RUSSIAN ###

# TODO
RU_THESISES_EXTRACTION_SYSTEM_PROMPT = \
'''
Задача: Основная цель - тщательно собрать информацию из входного текста и организовать эти данные в четкий, структурированный граф знаний.

Руководство по построению графа знаний:

Создание узлов и тезисов: Узлы должны изображать сущности или понятия, подобно узлам Википедии. Используй структурированный формат тезисов для сбора данных. Например, из фразы "Альберт Эйнштейн родился в Германии и известен разработкой теории относительности" извлеки "Альберт Эйнштейн родился в Германии; ['Альберт Эйнштейн', 'Германия', 'рождение']. Альберт Эйнштейн разработал теорию относительности; ['Альберт Ейнштейн', 'разработка', 'Теория относительности'].".
Ты должен извлекать только конкретные знания, любые предположения должны быть описаны как гипотеза.
Например, из фразы "Джон набрал много очков и потенциально может стать победителем" следует извлечь "Джон набрал много очков; ['Джон', 'очки']. Джон может стать победителем; ['Джон', 'победитель']." и не следует извлекать "Джон станет победителем".
Помни, что узлы должны быть атомарными единицами, в то время как тезисы могут быть более сложными и длинными.

Не пропускай важную информацию. Если в наблюдении говорится, что "книга рассказывает историю о рыцаре, которому нужно убить дракона", тезисы должны быть такими: "книга рассказывает о рыцаре; ['книга', 'рыцарь']", "рыцарю нужно убить дракона; ['рыцарь', 'дракон']". Если наблюдение включает какой-то тип заметок, не забудь включить тезисы о том, что включает в себя эта заметка.
Между отдельными частями наблюдений могут существовать связи. Например, если в начале наблюдения говорится о том, что ты находишься в локации, а в конце - о том, что есть выход на восток, следует извлечь тезис: "В локации есть выход на восток; ['локация', 'выход', 'восток']".
Можно извлечь несколько тезисов, содержащих информацию об одном и том же узле. Например, "на кухне есть яблоко", "на кухне есть стол", "яблоко лежит на столе". Не пропускай этот тип связей.
Другие примеры тезисов: "комната z содержит черный шкафчик", "комната x имеет выход на восток", "яблоко лежит на столе", "ключ находится в шкафчике", "яблоко нужно приготовить на гриле", "картофель нужно нарезать", "плита используется для жарки", "рецепт требует зеленого яблока", "рецепт требует картофеля".
Не используй "none" в качестве одного из узлов.
Тезисы должны быть понятными и последовательными, поэтому ты можешь оформить их в виде предложений. Лучше сделать более длинный тезис, чем разделить его на два, которые будут противоречить друг другу.
Например, лучше составить тезис "Северный выход из кухни заблокирован дверью", чем "в кухне есть дверь" и "северный выход заблокирован дверью".
потому что без контекста кухни "северный выход заблокирован дверью" может относиться к любой комнате дома.

Помни, что тезисы должны быть извлечены в формате: "тезис_1; [список объектов для тезиса_1]. тезис2; [список объектов для тезиса_2]." и т. д.

В качестве ответа сгенерируй только извлеченные тезисы в формате, описанном выше, и не включай дополнительные пояснений результата.
'''

# TODO
RU_THESISES_EXTRACTION_USER_PROMPT = \
'''
Текст:
{text}
'''

# TODO
RU_THESISES_EXTRACTION_ASSISTANT_PROMPT = \
'''
Извлечённые тезисы:
'''
