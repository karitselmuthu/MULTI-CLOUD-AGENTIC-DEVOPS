"""Check that a retrieved answer cites only supplied source revisions."""

import re

from agents.knowledge.agent import KnowledgeAnswer
from knowledge.retrieval.citations import citation


CITATION = re.compile(r"\[([^\[\]]+@[^\[\]]+)\]")


def citations_are_grounded(answer: KnowledgeAnswer) -> bool:
    if not answer.sources:
        return answer.text == "No approved source was found for this request."
    allowed = {citation(hit.source, hit.revision) for hit in answer.sources}
    paragraphs = [part.strip() for part in answer.text.split("\n\n") if part.strip()]
    return bool(paragraphs) and all(
        (refs := CITATION.findall(paragraph)) and set(refs).issubset(allowed)
        for paragraph in paragraphs
    )
