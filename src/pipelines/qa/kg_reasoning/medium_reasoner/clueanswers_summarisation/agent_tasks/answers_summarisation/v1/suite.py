from .........utils import AgentTaskSuite

from .parsers import casumm_custom_parse
from .prompts import EN_CASUMM_SYSTEM_PROMPT, EN_CASUMM_USER_PROMPT, EN_CASUMM_ASSISTANT_PROMPT, \
        RU_CASUMM_SYSTEM_PROMPT, RU_CASUMM_USER_PROMPT, RU_CASUMM_ASSISTANT_PROMPT

EN_CASUMM_SUITE = AgentTaskSuite(
    system_prompt=EN_CASUMM_SYSTEM_PROMPT,
    user_prompt=EN_CASUMM_USER_PROMPT,
    assistant_prompt=EN_CASUMM_ASSISTANT_PROMPT,
    parse_answer_func=casumm_custom_parse
)

RU_CASUMM_SUITE = AgentTaskSuite(
    system_prompt=RU_CASUMM_SYSTEM_PROMPT,
    user_prompt=RU_CASUMM_USER_PROMPT,
    assistant_prompt=RU_CASUMM_ASSISTANT_PROMPT,
    parse_answer_func=casumm_custom_parse
)

CASUMM_SUITE_V1 = {'ru': RU_CASUMM_SUITE, 'en': EN_CASUMM_SUITE}