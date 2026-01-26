from .........utils import AgentTaskSuite

from .parsers import planenh_custom_parse

from .prompts import EN_PLANENH_SYSTEM_PROMPT, EN_PLANENH_USER_PROMPT, EN_PLANENH_ASSISTANT_PROMPT, \
        RU_PLANENH_SYSTEM_PROMPT, RU_PLANENH_USER_PROMPT, RU_PLANENH_ASSISTANT_PROMPT

EN_PLANENH_SUITE = AgentTaskSuite(
    system_prompt=EN_PLANENH_SYSTEM_PROMPT,
    user_prompt=EN_PLANENH_USER_PROMPT,
    assistant_prompt=EN_PLANENH_ASSISTANT_PROMPT,
    parse_answer_func=planenh_custom_parse
)

RU_PLANENH_SUITE = AgentTaskSuite(
    system_prompt=RU_PLANENH_SYSTEM_PROMPT,
    user_prompt=RU_PLANENH_USER_PROMPT,
    assistant_prompt=RU_PLANENH_ASSISTANT_PROMPT,
    parse_answer_func=planenh_custom_parse
)

PLANENH_SUITE_V1 = {'ru': RU_PLANENH_SUITE, 'en': EN_PLANENH_SUITE}