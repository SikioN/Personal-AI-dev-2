from .........utils import AgentTaskSuite

from .parsers import planinit_custom_parse

from .prompts import EN_PLANINIT_SYSTEM_PROMPT, EN_PLANINIT_USER_PROMPT, EN_PLANINIT_ASSISTANT_PROMPT, \
        RU_PLANINIT_SYSTEM_PROMPT, RU_PLANINIT_USER_PROMPT, RU_PLANINIT_ASSISTANT_PROMPT

EN_PLANINIT_SUITE = AgentTaskSuite(
    system_prompt=EN_PLANINIT_SYSTEM_PROMPT,
    user_prompt=EN_PLANINIT_USER_PROMPT,
    assistant_prompt=EN_PLANINIT_ASSISTANT_PROMPT,
    parse_answer_func=planinit_custom_parse
)

RU_PLANINIT_SUITE = AgentTaskSuite(
    system_prompt=RU_PLANINIT_SYSTEM_PROMPT,
    user_prompt=RU_PLANINIT_USER_PROMPT,
    assistant_prompt=RU_PLANINIT_ASSISTANT_PROMPT,
    parse_answer_func=planinit_custom_parse
)

PLANINIT_SUITE_V1 = {'ru': RU_PLANINIT_SUITE, 'en': EN_PLANINIT_SUITE}