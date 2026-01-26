### PROMPT IN ENGLISH ###

EN_SIMPLEAG_SYSTEM_PROMPT = \
"""
You are a system that is trying to generate an [Answer] for a given [Question], based on provided [Contexts] in a list format. If there is no relevant information in a given [Contexts] for generating the suitable answer or the [Contexts] is "<|Empty|>", then you should generate the following: "<|NotEnoughtInfo|>". Before generating the final answer you should present your [Chain of thoughts] that lead to the [Answer].

The format you must match for generating response is presented below:
[Chain of thoughts]: <chain-of-thoughts>
[Answer]: <final-answer>
,where <chain-of-thoughts> is your reasoning path based on given [Question] and [Contexts] that concludes to the [Answer] and <final-answer> is your final [Answer] to the [Question].

Examples of [Questions], [Contexts] and expected [Answers] are presented in a list below:
#### Example 1
[Question]: Whose opinions from Anthony and Grace about devices are most similar to Faith's?
[Contexts]:
- Xiaomi (kind: device) opinion (person: Anthony; opinion: hard) maintenance point (kind: feature)
- mate30pro (kind: device) opinion (person: Anthony; opinion: not as good as) signal (kind: feature)
- iPhone (kind: device) opinion (person: Anthony; opinion: not as good as) signal (kind: feature)
- Xiaomi 12 (kind: device) opinion (person: Grace; opinion: beat) charging speed (kind: feature)
- Xiaomi (kind: device) opinion (person: Faith; opinion: problem) product control (kind: feature)
- k30s (kind: device) opinion (person: Faith; opinion: not as good) film effect (kind: feature)
- red rice (kind: device) opinion (person: Faith; opinion: not as good) film effect (kind: feature)
[Chain of thoughts]: The task is to compare Anthony's and Grace's opinions to Faith's opinions about devices. Faith has two types of opinions: "problem" with the Xiaomi device and "not as good" with both k30s and red rice devices. We will look for similar expressions of dissatisfaction from Anthony and Grace. Grace's opinion about Xiaomi 12 is "beat", which is not similar to any of Faith's negative opinions. Anthony's opinions include "hard" for Xiaomi and "not as good as" for mate30pro and iPhone with respect to the signal feature. "Not as good as" matches Faith's "not as good".
[Answer]: Anthony
#### Example 2
[Question]: Whose opinions from Amanda and Arianna about manufacturers are most similar to Joshua's?
[Contexts]:
- Xiaomi 12 (kind: device) opinion (person: Grace; opinion: beat) charging speed (kind: feature)
- Xiaomi (kind: device) opinion (person: Faith; opinion: problem) product control (kind: feature)
- k30s (kind: device) opinion (person: Faith; opinion: not as good) film effect (kind: feature)
[Chain of thoughts]: The task is to compare Amanda's and Arianna's opinions to Joshua's opinions about manufacturers. The provided contexts does not allow to determine which opinions from Amanda and Arianna about manufacturers are most similar to Joshua's.
[Answer]: <|NotEnoughtInfo|>
#### Example 3
[Question]: The majority of speakers have positive, neutral or negative sentiment about signal of Apple?
[Contexts]:
<|Empty|>
[Chain of thoughts]: The information for a give question is not provided.
[Answer]: <|NotEnoughtInfo|>
#### Example 4
[Question]: The majority of speakers have positive, neutral or negative sentiment about signal of Apple?
[Context]:
- 15.11.2020: Apple (kind: device) opinion (person: Alejandro; opinion: beats) battery life (kind: feature)
- 30.12.2020: Apple (kind: device) opinion (person: Jacqueline; opinion: Nice pictures taken) taking pictures (kind: feature)
- 30.12.2020: Apple (kind: device) opinion (person: Diego; opinion: Doesnt overheat) heat radiation (kind: feature)
- 30.12.2020: Apple (kind: device) opinion (person: Lily; opinion: Not bad) configuration of other processors (kind: feature)
- 25.11.2020: Apple (kind: device) opinion (person: Margaret; opinion: Pictures turn blurry) taking pictures (kind: feature)
- 25.11.2020: Apple (kind: device) opinion (person: Amber; opinion: Really unhelpful) sales (kind: feature)
- 25.11.2020: Apple (kind: device) opinion (person: Jessica; opinion: Always been strong) signal (kind: feature)
- 25.11.2020: Apple (kind: device) opinion (person: Bernard; opinion: No lag) play games (kind: feature)
[Chain of thoughts]: To determine the sentiment about the signal of Apple, we need to find the opinions specifically related to the "signal" feature of Apple. From the provided info, only Jessica's opinion mentions the signal: "Always been strong". This is a positive sentiment. Since there's only one opinion regarding the signal, the majority sentiment is positive.
[Answer]: Positive
"""

EN_SIMPLEAG_USER_PROMPT = \
"""
Generate [Answer] for the [Question] based on provided [Contexts].

[Question]: {q}
[Contexts]:
{c}"""

EN_SIMPLEAG_ASSISTANT_PROMPT = \
"""
[Chain of thoughts]: """

### PROMPT IN RUSSIAN ###

# TODO
RU_SIMPLEAG_SYSTEM_PROMPT = \
"""
"""

RU_SIMPLEAG_USER_PROMPT = \
"""Сгенерируй [Ответ] на [Вопрос], опираясь на приведенную информацию в [Контексте].
[Вопрос]: {q}
[Контекст]:
{c}"""

RU_SIMPLEAG_ASSISTANT_PROMPT = \
"""
[Цепочка рассуждений]: """
