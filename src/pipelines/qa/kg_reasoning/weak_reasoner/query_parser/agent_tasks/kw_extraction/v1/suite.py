from .........utils import AgentTaskSuite

from .prompts import \
    EN_KWE_SYSTEM_PROMPT, EN_KWE_USER_PROMPT, EN_KWE_ASSISTANT_PROMPT,\
        RU_KWE_SYSTEM_PROMPT, RU_KWE_USER_PROMPT, RU_KWE_ASSISTANT_PROMPT

from .parsers import kwe_custom_parse

EN_KWE_SUITE = AgentTaskSuite(
    system_prompt=EN_KWE_SYSTEM_PROMPT,
    user_prompt=EN_KWE_USER_PROMPT,
    assistant_prompt=EN_KWE_ASSISTANT_PROMPT,
    parse_answer_func=kwe_custom_parse
)

RU_KWE_SUITE = AgentTaskSuite(
    system_prompt=RU_KWE_SYSTEM_PROMPT,
    user_prompt=RU_KWE_USER_PROMPT,
    assistant_prompt=RU_KWE_ASSISTANT_PROMPT,
    parse_answer_func=kwe_custom_parse
)

KWE_SUITE_V1 = {'ru': RU_KWE_SUITE, 'en': EN_KWE_SUITE}
