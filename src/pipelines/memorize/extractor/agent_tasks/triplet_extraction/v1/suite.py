from .......utils import AgentTaskSuite

from .parsers import etriplets_custom_parse
from .prompts import \
    EN_TRIPLETS_EXTRACTION_SYSTEM_PROMPT, EN_TRIPLETS_EXTRACTION_USER_PROMPT, \
        RU_TRIPLETS_EXTRACTION_SYSTEM_PROMPT, RU_TRIPLETS_EXTRACTION_USER_PROMPT


EN_TRIPLETS_EXTRACT_SUITE = AgentTaskSuite(
    system_prompt=EN_TRIPLETS_EXTRACTION_SYSTEM_PROMPT,
    user_prompt=EN_TRIPLETS_EXTRACTION_USER_PROMPT,
    assistant_prompt=None,
    parse_answer_func=etriplets_custom_parse
)

RU_TRIPLETS_EXTRACT_SUITE = AgentTaskSuite(
    system_prompt=RU_TRIPLETS_EXTRACTION_SYSTEM_PROMPT,
    user_prompt=RU_TRIPLETS_EXTRACTION_USER_PROMPT,
    assistant_prompt=None,
    parse_answer_func=etriplets_custom_parse
)

TRIPLET_EXTRACT_SUITE_V1 = {'ru': RU_TRIPLETS_EXTRACT_SUITE, 'en': EN_TRIPLETS_EXTRACT_SUITE}
