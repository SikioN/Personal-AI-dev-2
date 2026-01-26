### PROMPT IN ENGLISH ###

EN_TRIPLETS_EXTRACTION_SYSTEM_PROMPT = \
'''Objective: The main goal is to meticulously gather information from the input [Text] and organize this data into a clear, structured knowledge graph. Knowledge graphs consists of a set of triplets. Each triplet contains two entities (subject and object) and one relation
that connects these subject and object. The subject is the entity that takes or undergo the action expressed by the predicate. The object is the entity which is the factual object of the action. The information provided by each predicate can be summarized as a
knowledge triplet of the form "subject | predicate | object".

Requirements for building a knowledge graph:
1. Nodes must depict objects or concepts, usually in one or two words. Subjects and objects could be named entities or concepts describing a group of people, events, or abstract objects from the Wikidata knowledge graph.
2. Complex objects or concepts like "John | position | engineer in Google" must be splitted into simple ones like "John | position | engineer" and "John | work at | Google".
3. Length of the triplet should not be more than 7 words.
4. Extract only concrete knowledges, any assumptions must be described as hypothesis. For example, from [Text] "John have scored many points and potentially will be winner" extract "John | scored many | points", "John | could be | winner" and should not extract "John | will be | winner".
3. Object and subject in triplet must be an atomary units while relation can be more complex and long.
4. Do not miss important information. If [Text] is "book involves story about knight, who needs to kill a dragon", [Extracted Triplets] should be "book | involves | knight", "knight | needs to kill | dragon".
5. Several triplets can be extracted, that contain information about the same node. For example: "kitchen | contains | apple", "kitchen | contains | table", "apple | is on | table". Do not miss this type of connections.
6. Do not use "none" as objects/subject in triplet.

[Extracted triplets] should be returned in the following format:
subject_1 | relation_1 | object_1;
subject_2 | relation_2 | object_2;
...
subject_n | relation_n | object_n.

Examples of [Text] and expected [Extracted Triplets] are presented in a list below:
#### Example 1
[Text]:
Albert Einstein, born in Germany, is known for developing the theory of relativity.
[Extracted Triplets]:
Albert Einstein | country of birth | Germany;
Albert Einstein | developed | Theory of Relativity.
'''

# As a response generate only extracted triplets in the format, described above and do not include additional explanations of the obtained result.

EN_TRIPLETS_EXTRACTION_USER_PROMPT = \
'''
[Text]:
{text}
'''

EN_TRIPLETS_ASSISTANT_PROMPT = \
'''
[Extracted Triplets]:
'''

### PROMPT IN RUSSIAN ###

# TODO
RU_TRIPLETS_EXTRACTION_SYSTEM_PROMPT = \
'''Задача: Основная цель - скрупулезно собрать информацию из входного текста и организовать эти данные в четкий, структурированный граф знаний.

Рекомендации по построению графа знаний:

Создание узлов и триплетов: Узлы должны изображать сущности или понятия, подобно узлам Википедии. Используй структурированный формат триплетов для записи данных, например: "субъект, отношение, объект". Например, из "Альберт Эйнштейн, родившийся в Германии, известен разработкой теории относительности" извлеките "Альберт Эйнштейн, страна рождения, Германия; Альберт Эйнштейн, разработал, теория относительности".
Помни, что сложные триплеты вроде "Джон, должность, инженер в Google" следует разбивать на простые триплеты вроде "Джон, должность, инженер", "Джон, работа в, Google".
Длина триплета не должна превышать 7 слов. Вы должны извлекать только конкретные знания, любые предположения должны быть описаны как гипотеза.
Например, из фразы "Джон набрал много очков и потенциально станет победителем" следует извлечь "Джон, набрал много, очки; Джон, может стать, победитель" и не следует извлекать "Джон, станет, победитель".
Помни, что объект и субъект должны быть атомарными единицами, в то время как отношение может быть более сложным и длинным. Субъект, отношение и объект должны быть записаны в инфинитиве.

Не пропускай важную информацию. Если в наблюдении говорится, что "книга включает в себя историю о рыцаре, которому нужно убить дракона", то триплеты должны быть такими: "книга, включает в себя, рыцарь", "рыцарь, должен убить, дракон". Если наблюдение включает какие-то заметки, не забудь включить триплеты о том, что эта заметка включает в себя.
Между отдельными частями наблюдений могут существовать связи. Например, если в начале наблюдения говорится, что вы находитесь в локации, а в конце - что есть выход на восток, тебе следует извлечь триплет: 'локация, имеет выход, восток'.
Можно извлечь несколько триплетов, содержащих информацию об одном и том же узле. Например, "кухня, содержит, яблоко", "кухня, содержит, стол", "яблоко, находится на, стол". Не пропускай этот тип связей.
Другие примеры триплетов: "комната z, содержит, черный шкафчик"; "комната x, имеет выход на, восток", "яблоко, лежит на, стол", "ключ, находится в, шкафчик", "яблоко, нужно приготовить на, гриль".
Не используй "none" в качестве одной из сущностей.

Помни, что триплеты должны быть извлечены в формате: "субъект_1, отношение_1, объект_1; субъект_2, отношение_2, объект_2; ...".
Это важно
Не разделяй триплеты символом переноса строки, разделяйте триплеты символом ";". Каждый триплет должен содержать строго два символа ",".

В качестве ответа сгенерируй только извлеченные триплеты в формате, описанном выше, и не включай дополнительные пояснений результата.'''

# TODO
RU_TRIPLETS_EXTRACTION_USER_PROMPT = \
'''Текст:
{text} '''

# TODO
RU_TRIPLETS_ASSISTANT_PROMPT = \
'''
Извлеченные триплеты: '''
