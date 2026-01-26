from .......utils import AgentTaskSuite

from .parsers import en_subasumm_custom_answer_parse, ru_subasumm_custom_answer_parse

from .prompts import EN_SUBASUMM_SYSTEM_PROMPT, EN_SUBASUMM_USER_PROMPT, EN_SUBASUMM_ASSISTANT_PROMPT, \
        RU_SUBASUMM_SYSTEM_PROMPT, RU_SUBASUMM_USER_PROMPT, RU_SUBASUMM_ASSISTANT_PROMPT

EN_SUBASUMM_SUITE = AgentTaskSuite(
    system_prompt=EN_SUBASUMM_SYSTEM_PROMPT,
    user_prompt=EN_SUBASUMM_USER_PROMPT,
    assistant_prompt=EN_SUBASUMM_ASSISTANT_PROMPT,
    parse_answer_func=en_subasumm_custom_answer_parse
)

RU_SUBASUMM_SUITE = AgentTaskSuite(
    system_prompt=RU_SUBASUMM_SYSTEM_PROMPT,
    user_prompt=RU_SUBASUMM_USER_PROMPT,
    assistant_prompt=RU_SUBASUMM_ASSISTANT_PROMPT,
    parse_answer_func=ru_subasumm_custom_answer_parse
)

SUBASUMM_SUITE_V1 = {'ru': RU_SUBASUMM_SUITE, 'en': EN_SUBASUMM_SUITE}
