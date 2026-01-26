from ........utils import AgentTaskSuite

from .parsers import qd_custom_parse

from .prompts import EN_QD_SYSTEM_PROMPT, EN_QD_USER_PROMPT, EN_QD_ASSISTANT_PROMPT, \
        RU_QD_SYSTEM_PROMPT, RU_QD_USER_PROMPT, RU_QD_ASSISTANT_PROMPT

EN_QD_SUITE = AgentTaskSuite(
    system_prompt=EN_QD_SYSTEM_PROMPT,
    user_prompt=EN_QD_USER_PROMPT,
    assistant_prompt=EN_QD_ASSISTANT_PROMPT,
    parse_answer_func=qd_custom_parse
)

RU_QD_SUITE = AgentTaskSuite(
    system_prompt=RU_QD_SYSTEM_PROMPT,
    user_prompt=RU_QD_USER_PROMPT,
    assistant_prompt=RU_QD_ASSISTANT_PROMPT,
    parse_answer_func=qd_custom_parse
)

QD_SUITE_V1 = {'ru': RU_QD_SUITE, 'en': EN_QD_SUITE}
