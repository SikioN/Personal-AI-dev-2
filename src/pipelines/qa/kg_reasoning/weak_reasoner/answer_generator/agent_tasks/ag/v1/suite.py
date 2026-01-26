from .........utils import AgentTaskSuite

from .parsers import ru_simpleag_custom_parse, en_simpleag_custom_parse

from .prompts import EN_SIMPLEAG_SYSTEM_PROMPT, EN_SIMPLEAG_USER_PROMPT, EN_SIMPLEAG_ASSISTANT_PROMPT,\
        RU_SIMPLEAG_SYSTEM_PROMPT, RU_SIMPLEAG_USER_PROMPT, RU_SIMPLEAG_ASSISTANT_PROMPT

EN_SIMPLEAG_SUITE = AgentTaskSuite(
    system_prompt=EN_SIMPLEAG_SYSTEM_PROMPT,
    user_prompt=EN_SIMPLEAG_USER_PROMPT,
    assistant_prompt=EN_SIMPLEAG_ASSISTANT_PROMPT,
    parse_answer_func=en_simpleag_custom_parse
)

RU_SIMPLEAG_SUITE = AgentTaskSuite(
    system_prompt=RU_SIMPLEAG_SYSTEM_PROMPT,
    user_prompt=RU_SIMPLEAG_USER_PROMPT,
    assistant_prompt=RU_SIMPLEAG_ASSISTANT_PROMPT,
    parse_answer_func=ru_simpleag_custom_parse
)

SIMPLEAG_SUITE_V1 = {'ru': RU_SIMPLEAG_SUITE, 'en': EN_SIMPLEAG_SUITE}
