EN_DC_SYSTEM_PROMPT = '''
Given a question you are asked to determine whether it can be decomposed on several independent questions that can be answered in isolation to eachother. Answer 'Yes' or 'No'. Before generating the answer you should present your chain of thoughts.

The format you must match for generating response is presented below:
[Chain of thoughts]
<chain-of-thoughts>
[Answer]
<final-answer>
,where <chain-of-thoughts> is your reasoning path based on given question that concludes to the answer and <final-answer> is your Yes/No-answer.
'''

EN_DC_USER_PROMPT = '''
[Base question]
{query}
'''
EN_DC_ASSISTANT_PROMPT = '''
[Chain of thoughts]
'''

RU_DC_SYSTEM_PROMPT = ... # TODO
RU_DC_USER_PROMPT = ... # TODO
RU_DC_ASSISTANT_PROMPT = ... # TODO