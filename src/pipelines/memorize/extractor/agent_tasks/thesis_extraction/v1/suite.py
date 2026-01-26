from .......utils import AgentTaskSuite

from .parsers import ethesises_custom_parse
from .prompts import \
    EN_THESISES_EXTRACTION_SYSTEM_PROMPT, EN_THESISES_EXTRACTION_USER_PROMPT, \
        RU_THESISES_EXTRACTION_SYSTEM_PROMPT, RU_THESISES_EXTRACTION_USER_PROMPT


EN_THESISES_EXTRACT_SUITE = AgentTaskSuite(
    system_prompt=EN_THESISES_EXTRACTION_SYSTEM_PROMPT,
    user_prompt=EN_THESISES_EXTRACTION_USER_PROMPT,
    assistant_prompt=None,
    parse_answer_func=ethesises_custom_parse
)

RU_THESISES_EXTRACT_SUITE = AgentTaskSuite(
    system_prompt=RU_THESISES_EXTRACTION_SYSTEM_PROMPT,
    user_prompt=RU_THESISES_EXTRACTION_USER_PROMPT,
    assistant_prompt=None,
    parse_answer_func=ethesises_custom_parse
)

THESIS_EXTRACT_SUITE_V1 = {'ru': RU_THESISES_EXTRACT_SUITE, 'en': EN_THESISES_EXTRACT_SUITE}
