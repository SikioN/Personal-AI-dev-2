EN_PLANENH_SYSTEM_PROMPT = '''
Given a question, associated search-plan and finded information at current moment based on them (search-queries), you need to enhance/reformulate next search-queries to find more relevant information for generation of more accurate answer.

Generate enhanced next search-queries in the following format:
1. <sub-query1>
2. <sub-query2>
...
N. <sub-queryN>
'''

EN_PLANENH_USER_PROMPT = '''
[Question]
{query}

[Complited search-plan queries]
{complited_squeries}

[Next search-plan queries at now]
{next_squeries}
'''

EN_PLANENH_ASSISTANT_PROMPT = '''
[Enhanced next search-plan queries]
'''

RU_PLANENH_SYSTEM_PROMPT = ... # TODO
RU_PLANENH_USER_PROMPT = ... # TODO 
RU_PLANENH_ASSISTANT_PROMPT = ... # TODO