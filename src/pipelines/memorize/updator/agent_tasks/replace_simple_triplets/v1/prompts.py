RU_REPLACE_SIMPLE_SYSTEM_PROMPT = """Ты - ассистент, который умеет решать заданные задачи."""

RU_REPLACE_SIMPLE_USER_PROMPT = """Тебе будет предоставлен список существующих и список новых триплетов. Тройки имеют следующий формат: «субъект, отношение, объект».
Триплеты обозначают факты о мире. Окружение меняется, поэтому некоторые триплеты из списка существующих триплетов могут быть заменены одним из новых триплетов. Например, игрок взял предмет из шкафчика, и существующая тройка «предмет, находится в, шкафчик» должна быть заменена на новую тройку «предмет, находится в, инвентарь».

Иногда триплеты для замены отсутствуют:
Пример существующих триплетов: «Золотой шкафчик, состояние, открытый»; „Комната K, находится к западу от, комната I“; „Комната K, имеет выход, восточный“.
Пример новых триплетов: «Комната T, находится к северу от, комната N»; „Комната T, имеет выход на, юг“.
Пример замены: []. Заменять здесь нечего

Иногда несколько триплетов можно заменить одним:
Пример существующих троек: "кухня, содержит, веник"; "веник, находится на, пол".
Пример новых троек: "метла, находится в, инвентарь".
Пример замены: [[«кухня, содержит, веник» -> «веник, находится в, инвентарь»], [«веник, находится на, пол» -> «веник, находится в, инвентарь»]]. Потому что веник сменил местоположение с пола на кухне на инвентарь игрока.

Убедитесь, что триплеты заменяются только в том случае, если они содержат избыточную или противоречивую информацию об одном и том же аспекте сущности. Триплеты не должны заменяться, если они предоставляют отличную или дополнительную информацию о сущностях по сравнению с новыми триплетами. В частности, рассмотрите отношения, свойства или контексты, описываемые каждой тройкой, и убедитесь, что они совпадают перед заменой. Если существует неопределенность в отношении того, следует ли заменять триплет, отдайте предпочтение сохранению существующего триплета, а не его замене. При сравнении существующих и новых триплетов, если они относятся к разным аспектам или атрибутам сущностей, не заменяйте их. Замены должны происходить только в случае семантического дублирования между существующим и новым триплетом.
Пример существующих триплетов: 'яблоко, будет, приготовлено', 'нож, используется для, нарезка', 'яблоко, было, нарезано'.
Пример новых триплетов: "яблоко, лежит на, столе", "кухня, содержит, нож", "яблоко, было, запечено".
Пример замены: []. Заменять здесь нечего. Эти триплеты описывают разные свойства предметов, поэтому их не следует заменять.

Еще один пример того, когда не следует заменять существующие тройки:
Пример существующих триплетов: "кисть, используется для, рисования".
Пример новых триплетов: "кисть, находится в, художественный класс".
Пример замены: []. Заменять здесь нечего. Эти триплеты описывают разные свойства кисти, поэтому их не следует заменять.

Повторяю, не заменяйте триплеты, если они несут разную информацию о сущностях!!! Лучше оставить триплет, чем заменить тот, который несет важную информацию. Не утверждайте, что триплет нужно заменить, если вы в этом не уверены!!!
Если вы нашли триплет в существующих триплетах, который семантически дублирует некоторый триплет в новых триплетах, замените такой триплет из существующих триплетов. Однако не заменяйте триплеты, если они относятся к разным вещам.
####

Генерировать только замены, описания не нужны.
Существующие триплеты: {ex_triplets}.
Новые триплеты: {new_triplets}.
####
Внимание! Замены должны формироваться строго в следующем формате: [[устаревший_триплет_1 -> актуальный_триплет_1], [устаревший_триплет_2 -> актуальный_триплет_2], ...], вы НЕ ДОЛЖНЫ включать в ответ никаких описаний.
Замена: """

EN_REPLACE_SIMPLE_USER_PROMPT = """You will be provided with list of existing triplets and list of new triplets. Triplets are in the following format: "subject, relation, object".
The triplets denote facts about the environment where the player moves. The player takes actions and the environment changes, so some triplets from the list of existing triplets can be replaced with one of the new triplets. For example, the player took the item from the locker and the existing triplet "item, is in, locker" should be replaced with the new triplet "item, is in, inventory".

Sometimes there are no triplets to replace:
Example of existing triplets: "Golden locker, state, open"; "Room K, is west of, Room I"; "Room K, has exit, east".
Example of new triplets: "Room T, is north of, Room N"; "Room T, has exit, south".
Example of replacing: []. Nothisg to replace here

Sometimes several triplets can be replaced with one:
Example of existing triplets: "kitchen, contains, broom"; "broom, is on, floor".
Example of new triplets: "broom, is in, inventory".
Example of replacing: [["kitchen, contains, broom" -> "broom, is in, inventory"], ["broom, is on, floor" -> "broom, is in, inventory"]]. Because broom changed location from the floor in the kitchen to players inventory.

Ensure that triplets are only replaced if they contain redundant or conflicting information about the same aspect of an entity. Triplets should not be replaced if they provide distinct or complementary information about entities compared to the new triplets. Specifically, consider the relationships, properties, or contexts described by each triplet and verify that they align before replacement. If there is uncertainty about whether a triplet should be replaced, prioritize retaining the existing triplet over replacing it. When comparing existing and new triplets, if they refer to different aspects or attributes of entities, do not replace them. Replacements should only occur when there is semantic duplication between an existing triplet and a new triplet.
Example of existing triplets: "apple, to be, cooked", 'knife, used for, cutting', 'apple, has been, sliced'
Example of new triplets: "apple, is on, table", 'kitchen, contsins, knife', 'apple, has beed, grilled'.
Example of replacing: []. Nothing to replace here. These triplets describe different properties of items, so they should not be replaced.

Another example of when not to replase existung triplets:
Example of existing triplets: "brush, used for, painting".
Example of new triplets: "brush, is in, art class".
Example of replacing: []. Nothing to replace here. These triplets describe different properties of brush, so they should not be replaced.

I repeat, do not replace triplets, if they carry differend type of information about entities!!! It is better to leave a tripplet, than to replace the one that has important information. Do not state that triplet needs to be replaced if you are not sure!!!
If you find triplet in Existing triplets which semantically duplicate some triplet in New triplets, replace such triplet from Existing triplets. However do not replace triplets if they refer to different things.
####

Generate only replacing, no descriptions are needed.
Existing triplets: {ex_triplets}.
New triplets: {new_triplets}.
####
Warning! Replacing must be generated strictly in following format: [[outdated_triplet_1 -> actual_triplet_1], [outdated_triplet_2 -> actual_triplet_2], ...], you MUST NOT include any descriptions in answer.
Replacing: """

EN_REPLACE_SIMPLE_SYSTEM_PROMPT = """You are a helpful assistant."""
