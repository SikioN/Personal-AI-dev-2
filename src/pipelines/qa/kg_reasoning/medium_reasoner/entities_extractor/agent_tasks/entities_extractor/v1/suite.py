from .........utils import AgentTaskSuite

from .parsers import entextr_custom_parse

from .prompts import EN_ENTEXTR_SYSTEM_PROMPT, EN_ENTEXTR_USER_PROMPT, EN_ENTEXTR_ASSISTANT_PROMPT, \
        RU_ENTEXTR_SYSTEM_PROMPT, RU_ENTEXTR_USER_PROMPT, RU_ENTEXTR_ASSISTANT_PROMPT

EN_ENTEXTR_SUITE = AgentTaskSuite(
    system_prompt=EN_ENTEXTR_SYSTEM_PROMPT,
    user_prompt=EN_ENTEXTR_USER_PROMPT,
    assistant_prompt=EN_ENTEXTR_ASSISTANT_PROMPT,
    parse_answer_func=entextr_custom_parse
)

RU_ENTEXTR_SUITE = AgentTaskSuite(
    system_prompt=RU_ENTEXTR_SYSTEM_PROMPT,
    user_prompt=RU_ENTEXTR_USER_PROMPT,
    assistant_prompt=RU_ENTEXTR_ASSISTANT_PROMPT,
    parse_answer_func=entextr_custom_parse
)

ENTEXTR_SUITE_V1 = {'ru': RU_ENTEXTR_SUITE, 'en': EN_ENTEXTR_SUITE}
