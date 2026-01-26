### PROMPT IN ENGLISH ###

EN_SIMPLEAG_SYSTEM_PROMPT = """You are a helpful assistant."""

EN_SIMPLEAG_USER_PROMPT = \
"""Answer the question, based on provided info by analogy with examples given. Generate chain of thought and then give the final answer in the following format:
### Answer
Chain of thought: ... Final answer: ...
Question 1: Whose opinions from Anthony and Grace about devices are most similar to Faith's?
Info 1:
- Xiaomi (kind: device) opinion (person: Anthony; opinion: hard) maintenance point (kind: feature)
- mate30pro (kind: device) opinion (person: Anthony; opinion: not as good as) signal (kind: feature)
- iPhone (kind: device) opinion (person: Anthony; opinion: not as good as) signal (kind: feature)
- Xiaomi 12 (kind: device) opinion (person: Grace; opinion: beat) charging speed (kind: feature)
- Xiaomi (kind: device) opinion (person: Faith; opinion: problem) product control (kind: feature)
- k30s (kind: device) opinion (person: Faith; opinion: not as good) film effect (kind: feature)
- red rice (kind: device) opinion (person: Faith; opinion: not as good) film effect (kind: feature)
### Answer 1
Chain of thought 1: The task is to compare Anthony's and Grace's opinions to Faith's opinions about devices. Faith has two types of opinions: "problem" with the Xiaomi device and "not as good" with both k30s and red rice devices. We will look for similar expressions of dissatisfaction from Anthony and Grace. Grace's opinion about Xiaomi 12 is "beat", which is not similar to any of Faith's negative opinions. Anthony's opinions include "hard" for Xiaomi and "not as good as" for mate30pro and iPhone with respect to the signal feature. "Not as good as" matches Faith's "not as good".
Final answer 1: Anthony
Question 2: The majority of speakers have positive, neutral or negative sentiment about signal of Apple?
Info 2:
- 15.11.2020: Apple (kind: device) opinion (person: Alejandro; opinion: beats) battery life (kind: feature)
- 30.12.2020: Apple (kind: device) opinion (person: Jacqueline; opinion: Nice pictures taken) taking pictures (kind: feature)
- 30.12.2020: Apple (kind: device) opinion (person: Diego; opinion: Doesnt overheat) heat radiation (kind: feature)
- 30.12.2020: Apple (kind: device) opinion (person: Lily; opinion: Not bad) configuration of other processors (kind: feature)
- 25.11.2020: Apple (kind: device) opinion (person: Margaret; opinion: Pictures turn blurry) taking pictures (kind: feature)
- 25.11.2020: Apple (kind: device) opinion (person: Amber; opinion: Really unhelpful) sales (kind: feature)
- 25.11.2020: Apple (kind: device) opinion (person: Jessica; opinion: Always been strong) signal (kind: feature)
- 25.11.2020: Apple (kind: device) opinion (person: Bernard; opinion: No lag) play games (kind: feature)
### Answer 2
Chain of thought 2: To determine the sentiment about the signal of Apple, we need to find the opinions specifically related to the "signal" feature of Apple. From the provided info, only Jessica's opinion mentions the signal: "Always been strong". This is a positive sentiment. Since there's only one opinion regarding the signal, the majority sentiment is positive.
Final answer 2: Positive
Question 3: {q}
Info 3:
{c}
### Answer 3
"""

EN_SIMPLEAG_ASSISTANT_PROMPT = ""

### PROMPT IN RUSSIAN ###

RU_SIMPLEAG_SYSTEM_PROMPT = """Ты - ассистент, который умеет решать заданные задачи."""

RU_SIMPLEAG_USER_PROMPT = \
"""Ответь на вопрос, опираясь на приведенную информацию.
Вопрос: {q}
Информация для ответа: {c}
Ответ: """

RU_SIMPLEAG_ASSISTANT_PROMPT = ""
