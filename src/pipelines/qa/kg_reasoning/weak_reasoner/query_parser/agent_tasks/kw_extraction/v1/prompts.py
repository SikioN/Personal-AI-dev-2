### PROMPT IN ENGLISH ###

EN_KWE_SYSTEM_PROMPT = \
'''You are a helpful assistant.'''

EN_KWE_USER_PROMPT = \
'''You are an expert system that can extract key entities from text. Key entities is a noun or an object like persone, device, company and etc. Extract such entities from the given text and present the results in the following format: <entitie1> | <entitie2> | ... | <entitieN>. Generate only entities and dont return some additional text. Examples of texts and extracted entities are listed below:
Text 1: Kayla has positive, negative or neutral opinion about video of Xiaomi 10Pro?
Entities 1: Kayla | opinion | video | Xiaomi 10Pro.
Text 2: Which device is better in battery life: Apple or k30u?
Entities 2: device | battery life | Apple | k30u.
Text 3: The majority of speakers have positive, neutral or negative sentiment about screen of Samsung?
Entities 3: speakers | sentiment | screen | Samsung.
Text 4: Which people have positive opinion about video of Xiaomi 10Pro on 25.11.2020?
Entities 4: people | opinion | video | Xiaomi 10Pro | 25.11.2020.

Text: {text}
Entities: '''

EN_KWE_ASSISTANT_PROMPT = "" 

### PROMPT IN RUSSIAN ###

RU_KWE_SYSTEM_PROMPT = \
'''Ты - ассистент, который умеет решать заданные задачи.'''

RU_KWE_USER_PROMPT = \
'''Вы экспертная система, которая может извлекать ключевые сущности из текста. Ключевые сущности — это существительное или объект, например персона, устройство, компания и т. д. Извлеките такие сущности из заданного текста и представьте результаты в следующем формате: <entitie1> | <entitie2> | ... | <entitieN>. Сгенерируйте только сущности и не возвращайте дополнительный текст. Примеры текстов и извлеченных сущностей приведены ниже:
Текст 1: У Кайлы положительное, отрицательное или нейтральное мнение о видео Xiaomi 10Pro?
Сущности 1: Кайла | мнение | видео | Xiaomi 10Pro.
Текст 2: Какое устройство лучше по времени работы от батареи: Apple или k30u?
Сущности 2: устройство | время работы от батареи | Apple | k30u.
Текст 3: Большинство говорящих положительно, нейтрально или отрицательно относятся к экрану Samsung?
Сущности 3: динамики | настроение | экран | Samsung.
Текст 4: Какие люди имеют положительное мнение о видео Xiaomi 10Pro от 25.11.2020?
Сущности 4: люди | мнение | видео | Xiaomi 10Pro | 25.11.2020.

Текст: {text}
Сущности: '''


RU_KWE_ASSISTANT_PROMPT = ""