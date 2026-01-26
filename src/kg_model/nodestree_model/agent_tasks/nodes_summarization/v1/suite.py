from ......utils import AgentTaskSuite

from .prompts import \
    EN_SUMMN_SYSTEM_PROMPT, EN_SUMMN_USER_PROMPT, EN_SUMMN_ASSISTANT_PROMPT,\
        RU_SUMMN_SYSTEM_PROMPT, RU_SUMMN_USER_PROMPT, RU_SUMMN_ASSISTANT_PROMPT

from .parsers import summn_custom_parse

EN_SUMMN_SUITE = AgentTaskSuite(
    system_prompt=EN_SUMMN_SYSTEM_PROMPT,
    user_prompt=EN_SUMMN_USER_PROMPT,
    assistant_prompt=EN_SUMMN_ASSISTANT_PROMPT,
    parse_answer_func=summn_custom_parse
)

RU_SUMMN_SUITE = AgentTaskSuite(
    system_prompt=RU_SUMMN_SYSTEM_PROMPT,
    user_prompt=RU_SUMMN_USER_PROMPT,
    assistant_prompt=RU_SUMMN_ASSISTANT_PROMPT,
    parse_answer_func=summn_custom_parse
)

SUMMN_SUITE_V1 = {'ru': RU_SUMMN_SUITE, 'en': EN_SUMMN_SUITE}
