from ........utils import AgentTaskSuite

from .parsers import dc_custom_answer_parse
from .prompts import EN_DC_SYSTEM_PROMPT, EN_DC_USER_PROMPT, EN_DC_ASSISTANT_PROMPT, \
        RU_DC_SYSTEM_PROMPT, RU_DC_USER_PROMPT, RU_DC_ASSISTANT_PROMPT

EN_DC_SUITE = AgentTaskSuite(
    system_prompt=EN_DC_SYSTEM_PROMPT,
    user_prompt=EN_DC_USER_PROMPT,
    assistant_prompt=EN_DC_ASSISTANT_PROMPT,
    parse_answer_func=dc_custom_answer_parse
)

RU_DC_SUITE = AgentTaskSuite(
    system_prompt=RU_DC_SYSTEM_PROMPT,
    user_prompt=RU_DC_USER_PROMPT,
    assistant_prompt=RU_DC_ASSISTANT_PROMPT,
    parse_answer_func=dc_custom_answer_parse
)

DC_SUITE_V1 = {'ru': RU_DC_SUITE, 'en': EN_DC_SUITE}
