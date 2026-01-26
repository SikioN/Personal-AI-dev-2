EN_ANSWGEN_SYSTEM_PROMPT = '''
Given a question, associated search-queries and finded information based on them, you are asked to answer the question only based on these knowledge. If there is no relevant information in a given finded information for generating the suitable answer, then you should generate the following: "<|NotEnoughtInfo|>". Before generating the answer you should present your chain of thoughts.

The format you must match for generating response is presented below:
[Chain of thoughts]
<chain-of-thoughts>
[Answer]
<final-answer>
,where <chain-of-thoughts> is your reasoning path based on given question,search-queries and finded information that concludes to the answer and <final-answer> is your final answer to the question.
'''

EN_ANSWGEN_USER_PROMPT = '''
[Question]
{query}

{search_info}
'''

EN_ANSWGEN_ASSISTANT_PROMPT = '''
[Chain of thoughts]
'''

RU_ANSWGEN_SYSTEM_PROMPT = ... # TODO
RU_ANSWGEN_USER_PROMPT = ... # TODO 
RU_ANSWGEN_ASSISTANT_PROMPT = ... # TODO