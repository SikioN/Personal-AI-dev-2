EN_ANSWCLS_SYSTEM_PROMPT = '''
Given a question, associated search-queries and finded information based on them, you are asked to determine whether it’s sufficient for you to answer this question based on a given knowledge. Answer 'Yes' or 'No'. Before generating the answer you should present your chain of thoughts.

The format you must match for generating response is presented below:
[Chain of thoughts]
<chain-of-thoughts>
[Answer]
<final-answer>
,where <chain-of-thoughts> is your reasoning path based on given question, search-queries and finded information that concludes to the answer and <final-answer> is your Yes/No-answer.
'''

EN_ANSWCLS_USER_PROMPT = '''
[Question]
{query}

{search_info}
'''

EN_ANSWCLS_ASSISTANT_PROMPT = '''
[Chain of thoughts]
''' 

RU_ANSWCLS_SYSTEM_PROMPT = ... # TODO
RU_ANSWCLS_USER_PROMPT = ... # TODO 
RU_ANSWCLS_ASSISTANT_PROMPT = ... # TODO