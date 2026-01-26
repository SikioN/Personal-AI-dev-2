EN_ENHCLS_SYSTEM_PROMPT = '''
Given a question, associated search-plan and finded information at current moment based on them (search-queries), you are asked to determine whether next search-queries should be enhanced/modified to find more relevant information and generate more accurate answer. Answer 'Yes' or 'No'. Before generating the answer you should present your chain of thoughts.

The format you must match for generating response is presented below:
[Chain of thoughts]
<chain-of-thoughts>
[Answer]
<final-answer>
,where <chain-of-thoughts> is your reasoning path based on given question, search-plan and finded information at now that concludes to the answer and <final-answer> is your Yes/No-answer.
'''

EN_ENHCLS_USER_PROMPT = '''
[Question]
{query}

[Complited search-plan queries]
{complited_squeries}

[Next search-plan queries at now]
{next_squeries}
'''

EN_ENHCLS_ASSISTANT_PROMPT = '''
[Chain of thoughts]
'''

RU_ENHCLS_SYSTEM_PROMPT = ... # TODO
RU_ENHCLS_USER_PROMPT = ... # TODO 
RU_ENHCLS_ASSISTANT_PROMPT = ... # TODO