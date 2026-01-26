### PROMPT IN ENGLISH ###

EN_SUMMN_SYSTEM_PROMPT = \
'''
You are an expert system that can follow the rules and summarize given pices of information.
'''

EN_SUMMN_USER_PROMPT = \
'''
You will receive two pieces of information: New Information is detailed, and Existing Information is a summary from {n_descendants} previous entries. Your task is to merge these
into a single, cohesive summary that highlights the most important insights.
- Focus on the key points from both inputs.
- Ensure the final summary combines the insights from both pieces of information.
- If the number of previous entries in Existing Information is accumulating (more than 2), focus on summarizing more concisely, only capturing the overarching theme, and getting more abstract in your summary.

Output the summary directly.

[New Information]
{new_content}
[Existing Information (from {n_descendants} previous entries)]
{current_content}
'''

EN_SUMMN_ASSISTANT_PROMPT = \
'''
[Output Summary]
'''

### PROMPT IN RUSSIAN ###

RU_SUMMN_SYSTEM_PROMPT = ... # TODO

RU_SUMMN_USER_PROMPT = ... # TODO

RU_SUMMN_ASSISTANT_PROMPT = ... # TODO
