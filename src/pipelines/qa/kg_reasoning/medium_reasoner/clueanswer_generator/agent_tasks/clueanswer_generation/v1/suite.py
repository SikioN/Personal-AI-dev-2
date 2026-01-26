from .........utils import AgentTaskSuite

from .parsers import cagen_custom_parse

from .prompts import EN_CAGEN_SYSTEM_PROMPT, EN_CAGEN_USER_PROMPT, EN_CAGEN_ASSISTANT_PROMPT, \
        RU_CAGEN_SYSTEM_PROMPT, RU_CAGEN_USER_PROMPT, RU_CAGEN_ASSISTANT_PROMPT

EN_CAGEN_SUITE = AgentTaskSuite(
    system_prompt=EN_CAGEN_SYSTEM_PROMPT,
    user_prompt=EN_CAGEN_USER_PROMPT,
    assistant_prompt=EN_CAGEN_ASSISTANT_PROMPT,
    parse_answer_func=cagen_custom_parse
)

RU_CAGEN_SUITE = AgentTaskSuite(
    system_prompt=RU_CAGEN_SYSTEM_PROMPT,
    user_prompt=RU_CAGEN_USER_PROMPT,
    assistant_prompt=RU_CAGEN_ASSISTANT_PROMPT,
    parse_answer_func=cagen_custom_parse
)

CAGEN_SUITE_V1 = {'ru': RU_CAGEN_SUITE, 'en': EN_CAGEN_SUITE}