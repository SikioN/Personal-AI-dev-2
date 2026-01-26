### PROMPT IN ENGLISH ###

EN_TRIPLETS_EXTRACTION_SYSTEM_PROMPT = \
'''Objective: The main goal is to meticulously gather information from the text and organize this data into a clear, structured knowledge graph.

Guidelines for Building the Knowledge Graph:

Creating Nodes and Triplets: Nodes should depict objects or concepts, usually one or two words. Use a structured triplet format to capture data, as follows: "subject, relation, object". For example, from "Albert Einstein, born in Germany, is known for developing the theory of relativity," extract "Albert Einstein, country of birth, Germany; Albert Einstein, developed, Theory of Relativity."

THIS PARAGRAPH IS VERY IMPORTANT!!!
Remember that you should break complex objects or concepts like "John, position, engineer in Google" into simple ones like "John, position, engineer", "John, work at, Google".
Length of your triplet should not be more than 7 words. You should extract only concrete knowledges, any assumptions must be described as hypothesis.
For example, from phrase "John have scored many points and potentially will be winner" you should extract "John, scored many, points; John, could be, winner" and should not extract "John, will be, winner".
Remember that object and subject must be an atomary units while relation can be more complex and long.

Do not miss important information. If text is 'book involves story about knight, who needs to kill a dragon', triplets should be 'book, involves, knight', 'knight, needs to kill, dragon'. If observation involves some type of notes, do not forget to include triplets about entities this note includes.
There could be connections between distinct parts of observations. For example if there is information in the beginning of the observation that you are in location, and in the end it states that there is an exit to the east, you should extract triplet: 'location, has exit, east'.
Several triplets can be extracted, that contain information about the same node. For example 'kitchen, contains, apple', 'kitchen, contains, table', 'apple, is on, table'. Do not miss this type of connections.
Other examples of triplets: 'room z, contains, black locker'; 'room x, has exit, east', 'apple, is on, table', 'key, is in, locker', 'apple, to be, grilled', 'potato, to be, sliced', 'stove, used for, frying', 'recipe, requires, green apple', 'recipe, requires, potato'.
Do not include triplets that state the current location of an agent like 'you, are in, location'.
Do not use 'none' as one of the objects.
If there is information that you read something, do not forget to incluse triplets that state that entitie that you read contains information that you extract.'''

EN_TRIPLETS_EXTRACTION_USER_PROMPT = \
'''Text: {text}

Remember that triplets must be extracted in format: "subject_1, relation_1, object_1; subject_2, relation_2, object_2; ..."
This is important
Do not separate triplets with new line, separate triplets with ";". Every triplet must contain strictly 2 ",".
THIS IS IMPORTANT!!!
Remember that triplets must be extracted in format: "subject_1, relation_1, object_1; subject_2, relation_2, object_2; ..."

Extracted triplets: '''

### PROMPT IN RUSSIAN ###

RU_TRIPLETS_EXTRACTION_SYSTEM_PROMPT = \
'''Задача: Основная цель - скрупулезно собрать информацию из текста и организовать эти данные в четкий, структурированный граф знаний.

Рекомендации по построению графа знаний:

Создание узлов и триплетов: Узлы должны изображать сущности или понятия, подобно узлам Википедии. Используй структурированный формат триплетов для записи данных, например: "субъект, отношение, объект». Например, из "Альберт Эйнштейн, родившийся в Германии, известен разработкой теории относительности» извлеките "Альберт Эйнштейн, страна рождения, Германия; Альберт Эйнштейн, разработал, теория относительности».
Помни, что сложные триплеты вроде "Джон, должность, инженер в Google» следует разбивать на простые триплеты вроде "Джон, должность, инженер», "Джон, работа в, Google».
Длина триплета не должна превышать 7 слов. Вы должны извлекать только конкретные знания, любые предположения должны быть описаны как гипотеза.
Например, из фразы "Джон набрал много очков и потенциально станет победителем» следует извлечь "Джон, набрал много, очки; Джон, может стать, победитель» и не следует извлекать "Джон, станет, победитель».
Помни, что объект и субъект должны быть атомарными единицами, в то время как отношение может быть более сложным и длинным. Субъект, отношение и объект должны быть записаны в инфинитиве.

Не пропускай важную информацию. Если в наблюдении говорится, что "книга включает в себя историю о рыцаре, которому нужно убить дракона», то триплеты должны быть такими: "книга, включает в себя, рыцарь», "рыцарь, должен убить, дракон». Если наблюдение включает какие-то заметки, не забудь включить триплеты о том, что эта заметка включает в себя.
Между отдельными частями наблюдений могут существовать связи. Например, если в начале наблюдения говорится, что вы находитесь в локации, а в конце - что есть выход на восток, тебе следует извлечь триплет: 'location, has exit, east'.
Можно извлечь несколько триплетов, содержащих информацию об одном и том же узле. Например, 'кухня, содержит, яблоко', 'кухня, содержит, стол', 'яблоко, находится на, стол'. Не пропускай этот тип связей.
Другие примеры триплетов: 'комната z, содержит, черный шкафчик'; 'комната x, имеет выход на, восток', 'яблоко, лежит на, стол', 'ключ, находится в, шкафчик', 'яблоко, нужно приготовить на, гриль'.
Не используй 'none' в качестве одной из сущностей.'''

RU_TRIPLETS_EXTRACTION_USER_PROMPT = \
'''Текст: {text}

Помни, что триплеты должны быть извлечены в формате: "субъект_1, отношение_1, объект_1; субъект_2, отношение_2, объект_2; ...».

Извлеченные триплеты: '''
