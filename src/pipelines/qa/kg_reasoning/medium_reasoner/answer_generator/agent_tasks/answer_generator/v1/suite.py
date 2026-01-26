from .........utils import AgentTaskSuite

from .parsers import answgen_custom_parse

from .prompts import EN_ANSWGEN_SYSTEM_PROMPT, EN_ANSWGEN_USER_PROMPT, EN_ANSWGEN_ASSISTANT_PROMPT, \
        RU_ANSWGEN_SYSTEM_PROMPT, RU_ANSWGEN_USER_PROMPT, RU_ANSWGEN_ASSISTANT_PROMPT

EN_ANSWGEN_SUITE = AgentTaskSuite(
    system_prompt=EN_ANSWGEN_SYSTEM_PROMPT,
    user_prompt=EN_ANSWGEN_USER_PROMPT,
    assistant_prompt=EN_ANSWGEN_ASSISTANT_PROMPT,
    parse_answer_func=answgen_custom_parse
)

RU_ANSWGEN_SUITE = AgentTaskSuite(
    system_prompt=RU_ANSWGEN_SYSTEM_PROMPT,
    user_prompt=RU_ANSWGEN_USER_PROMPT,
    assistant_prompt=RU_ANSWGEN_ASSISTANT_PROMPT,
    parse_answer_func=answgen_custom_parse
)

ANSWGEN_SUITE_V1 = {'ru': RU_ANSWGEN_SUITE, 'en': EN_ANSWGEN_SUITE}