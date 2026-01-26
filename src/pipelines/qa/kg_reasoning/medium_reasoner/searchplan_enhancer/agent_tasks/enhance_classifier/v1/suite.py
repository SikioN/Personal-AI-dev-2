from .........utils import AgentTaskSuite

from .parsers import enhcls_custom_parse

from .prompts import EN_ENHCLS_SYSTEM_PROMPT, EN_ENHCLS_USER_PROMPT, EN_ENHCLS_ASSISTANT_PROMPT, \
        RU_ENHCLS_SYSTEM_PROMPT, RU_ENHCLS_USER_PROMPT, RU_ENHCLS_ASSISTANT_PROMPT

EN_ENHCLS_SUITE = AgentTaskSuite(
    system_prompt=EN_ENHCLS_SYSTEM_PROMPT,
    user_prompt=EN_ENHCLS_USER_PROMPT,
    assistant_prompt=EN_ENHCLS_ASSISTANT_PROMPT,
    parse_answer_func=enhcls_custom_parse
)

RU_ENHCLS_SUITE = AgentTaskSuite(
    system_prompt=RU_ENHCLS_SYSTEM_PROMPT,
    user_prompt=RU_ENHCLS_USER_PROMPT,
    assistant_prompt=RU_ENHCLS_ASSISTANT_PROMPT,
    parse_answer_func=enhcls_custom_parse
)

ENHCLS_SUITE_V1 = {'ru': RU_ENHCLS_SUITE, 'en': EN_ENHCLS_SUITE}