"""LLM-driven post-processing of raw transcripts.

clean()            — removes filler words, collapses repetitions, structures
                     the text, and appends a technical documentation block.
translate_summary() — translates the Documentation Technique section to English.
"""

from mistralai.client import Mistral

from pipeline.prompts import CLEANUP_PROMPT_EN, CLEANUP_PROMPT_FR, TRANSLATE_SUMMARY_PROMPT


def clean(raw_transcript: str, client: Mistral, language: str = "fr") -> str:
    """Return a cleaned, structured Markdown document from a raw transcript.

    Args:
        raw_transcript: Text as returned by the STT step.
        client: Authenticated Mistral client.
        language: "fr" or "en" — selects the appropriate cleanup prompt.
    """
    system_prompt = CLEANUP_PROMPT_FR if language == "fr" else CLEANUP_PROMPT_EN

    response = client.chat.complete(
        model="mistral-small-latest",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": raw_transcript},
        ],
    )
    return response.choices[0].message.content.strip()


def translate_summary(processed: str, client: Mistral) -> str:
    """Return an English translation of the Documentation Technique section.

    The returned string is the translated section only (starting with
    '## Technical Documentation').  The caller appends it to the document.
    """
    response = client.chat.complete(
        model="mistral-small-latest",
        messages=[
            {"role": "system", "content": TRANSLATE_SUMMARY_PROMPT},
            {"role": "user", "content": processed},
        ],
    )
    return response.choices[0].message.content.strip()
