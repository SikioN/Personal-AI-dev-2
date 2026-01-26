from .........utils import AgentTaskSuite

from .parsers import answcls_custom_parse

from .prompts import EN_ANSWCLS_SYSTEM_PROMPT, EN_ANSWCLS_USER_PROMPT, EN_ANSWCLS_ASSISTANT_PROMPT, \
        RU_ANSWCLS_SYSTEM_PROMPT, RU_ANSWCLS_USER_PROMPT, RU_ANSWCLS_ASSISTANT_PROMPT

EN_ANSWCLS_SUITE = AgentTaskSuite(
    system_prompt=EN_ANSWCLS_SYSTEM_PROMPT,
    user_prompt=EN_ANSWCLS_USER_PROMPT,
    assistant_prompt=EN_ANSWCLS_ASSISTANT_PROMPT,
    parse_answer_func=answcls_custom_parse
)

RU_ANSWCLS_SUITE = AgentTaskSuite(
    system_prompt=RU_ANSWCLS_SYSTEM_PROMPT,
    user_prompt=RU_ANSWCLS_USER_PROMPT,
    assistant_prompt=RU_ANSWCLS_ASSISTANT_PROMPT,
    parse_answer_func=answcls_custom_parse
)

ANSWCLS_SUITE_V1 = {'ru': RU_ANSWCLS_SUITE, 'en': EN_ANSWCLS_SUITE}