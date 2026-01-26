EN_CQGEN_SYSTEM_PROMPT = '''
Given a question, first group of entities that was extracted from that question and the second groups of entities that was matched to the first group as more specific values your task is to generate more specific question based on it.

Examples:
[Base question #1]
Which device manufacturers does Maria prefer?
[Matched entities]
Maria: Maria
device manufacturers: Apple
[Specific question]
Does Maria prefer Apple as device manufacturer?

[Base question #2]
Which people have positive opinion about screen of Mi 10pro on 22.12.2018?
[Matched entities]
people: Abraham
screen: window
Mi 10pro: mi 10pro
22.12.2018: 22.12.2018
[Specific questions]
Does Abraham have position opinion about window of Mi 10pro on 22.12.2018?
'''

EN_CQGEN_USER_PROMPT = '''
[Base question]
{query}
[Matched entities]
{matched_entities}
'''

EN_CQGEN_ASSISTANT_PROMPT = '''
[Specific question]
'''

RU_CQGEN_SYSTEM_PROMPT = ... # TODO
RU_CQGEN_USER_PROMPT = ... # TODO 
RU_CQGEN_ASSISTANT_PROMPT = ... # TODO