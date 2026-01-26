from .parsers import rt_custom_parse
from .prompts import RU_REPLACE_THESIS_USER_PROMPT, EN_REPLACE_THESIS_USER_PROMPT,\
    RU_REPLACE_THESIS_SYSTEM_PROMPT, EN_REPLACE_THESIS_SYSTEM_PROMPT

from .......utils import AgentTaskSuite

EN_REPLACE_THESIS_SUITE = AgentTaskSuite(
    system_prompt=EN_REPLACE_THESIS_SYSTEM_PROMPT,
    user_prompt=EN_REPLACE_THESIS_USER_PROMPT,
    assistant_prompt=None,
    parse_answer_func=rt_custom_parse
)

RU_REPLACE_THESIS_SUITE = AgentTaskSuite(
    system_prompt=RU_REPLACE_THESIS_SYSTEM_PROMPT,
    user_prompt=RU_REPLACE_THESIS_USER_PROMPT,
    assistant_prompt=None,
    parse_answer_func=rt_custom_parse
)

REPLACE_THESIS_SUITE_V1 = {'ru': RU_REPLACE_THESIS_SUITE, 'en': EN_REPLACE_THESIS_SUITE}
