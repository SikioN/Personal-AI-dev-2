from .........utils import AgentTaskSuite

from .parsers import cqgen_custom_parse
from .prompts import EN_CQGEN_SYSTEM_PROMPT, EN_CQGEN_USER_PROMPT, EN_CQGEN_ASSISTANT_PROMPT, \
        RU_CQGEN_SYSTEM_PROMPT, RU_CQGEN_USER_PROMPT, RU_CQGEN_ASSISTANT_PROMPT

EN_CQGEN_SUITE = AgentTaskSuite(
    system_prompt=EN_CQGEN_SYSTEM_PROMPT,
    user_prompt=EN_CQGEN_USER_PROMPT,
    assistant_prompt=EN_CQGEN_ASSISTANT_PROMPT,
    parse_answer_func=cqgen_custom_parse
)

RU_CQGEN_SUITE = AgentTaskSuite(
    system_prompt=RU_CQGEN_SYSTEM_PROMPT,
    user_prompt=RU_CQGEN_USER_PROMPT,
    assistant_prompt=RU_CQGEN_ASSISTANT_PROMPT,
    parse_answer_func=cqgen_custom_parse
)

CQGEN_SUITE_V1 = {'ru': RU_CQGEN_SUITE, 'en': EN_CQGEN_SUITE}