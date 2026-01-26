RU_REPLACE_THESIS_SYSTEM_PROMPT = '''Ты - ассистент, который умеет решать заданные задачи.'''

RU_REPLACE_THESIS_USER_PROMPT = '''Тебе будет предоставлен список существующих тезисов и список новых тезисов.
Тезисы обозначают факты о мире. Окружение меняется, поэтому некоторые тезисы из списка существующих тезисов можно заменить на один из новых тезисов. Например, игрок взял предмет из шкафчика, и существующий тезис «предмет находится в шкафчике» должен быть заменен новым тезисом «предмет находится в инвентаре».

Иногда тезисы, которые нужно заменить, отсутствуют:
Пример существующих тезисов: [«Золотой шкафчик открыт», «Комната K находится к западу от комната I», «Комната K имеет выход на восток»].
Пример новых тезисов: [«Комната T находится к северу от комната N», «Комната T имеет выход на юг»].
Пример замены: []. Здесь ничего заменять не нужно

Иногда несколько тезисов можно заменить одним:
Пример существующих тезисов: [«кухня имеет веник», «веник лежит на пол»].
Пример новых тезисов: [«веник находится в инвентарь»].
Пример замены: [«веник находится в инвентарь <- кухня содержит веник», «веник находится в инвентаре <- веник находится на полу»]. Потому что метла сменила местоположение с пола на кухне на инвентарь игрока.

Убедись, что тезисы заменяются только в том случае, если они содержат избыточную или противоречивую информацию об одном и том же аспекте сущности. Не следует заменять тезисы, если они предоставляют отличную или дополнительную информацию о сущности по сравнению с новыми тезисами. В частности, рассмотри отношения, свойства или контексты, описываемые каждым тезисом, и проверьте их соответствие перед заменой. Если есть неопределенность в том, следует ли заменить тезис, отдайте предпочтение сохранению существующего тезиса, а не его замене. При сравнении существующих и новых тезисов, если они относятся к разным аспектам или атрибутам сущностей, не заменяйте их. Замены должны происходить только в случае семантического дублирования между существующим и новым тезисами.
Пример существующих тезисов: [«яблоко нужно приготовить», «нож используется для нарезки», «яблоко было нарезано»].
Пример новых тезисов: [«яблоко лежит на столе», «кухня содержит нож», «яблоко было запечено»].
Пример замены: []. Заменять здесь нечего. Эти тезисы описывают разные свойства предметов, поэтому их не следует заменять.

Еще один пример того, когда не следует заменять существующие тезисы:
Пример существующих тезисов: [«кисть используется для рисования»].
Пример новых тезисов: [«кисть находится в художественном классе»].
Пример замены: []. Заменять здесь нечего. Эти тезисы описывают разные свойства кисти, поэтому их не следует заменять.

Повторяю, не заменяй тезисы, если они несут разную информацию о сущностях!!! Лучше оставить тезис, чем заменить тот, который несет важную информацию. Не утверждай, что тезис нужно заменить, если ты в этом не уверен!!!
Если ты обнаружил в существующих тезисах тезисы, которые семантически дублируют некоторые тезисы в новых тезисах, замени такие тезисы из существующих тезисов. Однако не заменяй тезисы, если они относятся к разным вещам.
Для каждого тезиса, который вы хотите заменить, вы должны найти замену в новых тезисах. Если нет четкой замены, не заменяйте существующие тезисы.
Замены должны содержать информацию о тех же свойствах, что и заменяемые утверждения, но включать более свежую информацию.
Ты ДОЛЖЕН сохранить существующие тезисы, если они содержат уникальную или актуальную информацию о сущностях.
Например, ты НЕ ДОЛЖЕН заменять тезис «бег осуществляется в кроссовках» на «кроссовки находятся в магазине».
####

Генерируй только список замен, описания не нужны.
Существующие тезисы: {ex_thesises}.
Новые тезисы: {new_thesises}.
####
Внимание! Замены должны формироваться строго в следующем формате: [«новый_тезис_1 <- устаревший_тезис_1»; «новый_тезис_2 <- устаревший_тезис_2»; ...], ты НЕ ДОЛЖЕН включать в ответ какие-либо описания.
Замена: '''

EN_REPLACE_THESIS_SYSTEM_PROMPT = '''You are a helpful assistant.'''

EN_REPLACE_THESIS_USER_PROMPT = '''You will be provided with list of existing thesises and list of new thesises.
The thesises denote facts about the environment where the player moves. The player takes actions and the environment changes, so some thesises from the list of existing thesises can be replaced with one of the new thesises. For example, the player took the item from the locker and the existing thesis "item is in locker" should be replaced with the new thesis "item is in inventory".

Sometimes there are no thesises to replace:
Example of existing thesises: ["Golden locker is open", "Room K is west of Room I", "Room K has exit to east"]
Example of new thesises: ["Room T is north of Room N", "Room T has exit to south"]
Example of replacing: []. Nothisg to replace here

Sometimes several thesises can be replaced with one:
Example of existing thesises: ["kitchen contains broom", "broom is on floor"]
Example of new thesises: ["broom is in inventory"]
Example of replacing: ["broom is in inventory <- kitchen contains broom", "broom is in inventory <- broom is on floor"]. Because broom changed location from the floor in the kitchen to players inventory.

Ensure that thesises are only replaced if they contain redundant or conflicting information about the same aspect of an entity. Thesises should not be replaced if they provide distinct or complementary information about entities compared to the new thesises. Specifically, consider the relationships, properties, or contexts described by each thesis and verify that they align before replacement. If there is uncertainty about whether a thesis should be replaced, prioritize retaining the existing thesis over replacing it. When comparing existing and new thesises, if they refer to different aspects or attributes of entities, do not replace them. Replacements should only occur when there is semantic duplication between an existing thesis and a new thesis.
Example of existing thesises: ["apple need to be cooked", 'knife used for cutting', 'apple has been sliced']
Example of new thesises: ["apple is on table", 'kitchen contains knife', 'apple has beed grilled']
Example of replacing: []. Nothing to replace here. These thesises describe different properties of items, so they should not be replaced.

Another example of when not to replase existung thesises:
Example of existing thesises: ["brush is used for painting"]
Example of new thesises: ["brush is in art class"]
Example of replacing: []. Nothing to replace here. These thesises describe different properties of brush, so they should not be replaced.

I repeat, do not replace thesises if they carry differend type of information about entities!!! It is better to leave a thesis, than to replace the one that has important information. Do not state that thesis needs to be replaced if you are not sure!!!
If you find thesis in Existing thesises which semantically duplicate some thesis in New thesises, replace such thesis from Existing thesises. However do not replace thesis if they refer to different things.
For every thesis you want to replace you must find replacement from new thesises. If there is no clear replacement, you must not replace existing thesis.
The replacements should contain information about the same properties as the statements being replaced, but must include more recent information.
You MUST save existing thesis if it contains unique or actual information about entities.
For example, you MUST NOT replace thesis "running is done with sneakers" with "sneakers located at store".
####

Generate only list of replacing, no descriptions are needed.
Existing thesises: {ex_thesises}.
New thesises: {new_thesises}.
####
Warning! Replacing must be generated strictly in following format: ["new_thesis_1 <- outdated_thesis_1"; "new_thesis_2 <- outdated_thesis_2"; ...], you MUST NOT include any descriptions in answer.
Replacing: '''
