from enum import Enum

BEGIN_OF_TEXT = "<|begin_of_text|>"
"""This is equivalent to the BOS token"""

EOT_ID = "<|eot_id|>"
"""This signifies the end of the message in a turn."""

START_HEADER_ID = "<|start_header_id|>"
"""These tokens enclose the role for a particular message. The possible roles can be: system, user, assistant."""

END_HEADER_ID = "<|end_header_id|>"
"""These tokens enclose the role for a particular message. The possible roles can be: system, user, assistant."""

END_OF_TEXT = "<|end_of_text|>"
"""This is equivalent to the EOS token. On generating this token, Llama 3 will cease to generate more tokens."""

# A prompt can optionally contain a single system message,
# or multiple alternating user and assistant messages,
# but always ends with the last user message followed by the assistant header.


class Role(Enum):
    """The role of the model."""

    USR = "user"
    SYS = "system"
    ASST = "assistant"


def generate_prompt_llama3(*, system: str, messages: list[dict[str, str]]) -> str:
    """Generate a prompt for the model.

    Args:
        system (str): The system message.
        messages (list[dict[str, str]]): The user and assistant messages.

    Returns:
        str: The generated prompt.
    """
    prompt = f"""{BEGIN_OF_TEXT}
    {START_HEADER_ID}
        {Role.SYS.value}
    {END_HEADER_ID}
        {system}
    {EOT_ID}
    """

    last_role = None
    for message in messages:
        for role, text in message.items():
            prompt += f"""
    {START_HEADER_ID}
        {role}
    {END_HEADER_ID}
        {text}
    {EOT_ID}
    """
            last_role = role

    if last_role == Role.USR.value:
        prompt += f"""
    {START_HEADER_ID}
        {Role.ASST.value}
    {END_HEADER_ID}
    """

    return prompt
