### PROMPT IN ENGLISH ###

EN_CAGEN_SYSTEM_PROMPT = \
"""
Given a question and finded information based on it, you are asked to recognize and summarize all relevant information, that can be used as a part of suitable context to generate the answer. If there is no relevant information in a given finded information, then you should generate the following: "<|NoRelevantInfo|>".
"""

EN_CAGEN_USER_PROMPT = \
"""
[Question]: 
{q}
[Finded Information]:
{c}
"""

EN_CAGEN_ASSISTANT_PROMPT = \
"""
[Relevant Summary]:
"""

RU_CAGEN_SYSTEM_PROMPT = ... # TODO
RU_CAGEN_USER_PROMPT = ... # TODO
RU_CAGEN_ASSISTANT_PROMPT = ... # TODO