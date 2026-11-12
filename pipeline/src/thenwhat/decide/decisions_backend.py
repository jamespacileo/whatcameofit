"""Backend B: OpenAI's Decisions API, which answers bounded questions without writing text.

It takes every item of a step in one request, so sixty candidate records are scored in
one fast call where the general-model backend needs three slow ones. Its probabilities
are the model's own estimate, like the other backend's, and are not calibrated.
"""

import re

from thenwhat.decide.core import BackendAnswer
from thenwhat.llm.decisions import MAX_QUESTIONS, Choice, Chosen, Decisions

NAME = "openai-decisions"
# A sum this far from 1 is rescaled; further off, the answer is left for the caller to refuse.
RESCALE_WITHIN = 0.1


class DecisionsBackend:
    name = NAME
    # How many items one call takes. decide_many reads this in place of its own default.
    batch_size = MAX_QUESTIONS

    def __init__(self, decisions: Decisions) -> None:
        self._decisions = decisions

    def answer(self, step: str, state: str, options: list[str]) -> BackendAnswer:
        question = Choice(
            "Choose the option that answers the question put in the input.",
            [(option, option) for option in options],
        )
        (chosen,) = self._decisions.choose(f"decision:{step}", evidence=state, questions=[question])
        if chosen is None:
            raise ValueError("The Decisions API gave no answer.")
        return self._as_answer(chosen)

    def answer_many(
        self, step: str, intro: str, question: str, items: list[str], options: list[str]
    ) -> list[BackendAnswer | None]:
        """One request for all the items: the intro is the shared evidence, and each item
        is its own question."""
        described = _descriptions(question, options)
        chosen = self._decisions.choose(
            f"decision:{step}",
            evidence=intro,
            questions=[Choice(f"{question}\n\n{text}", described) for text in items],
        )
        return [None if one is None else self._as_answer(one) for one in chosen]

    def _as_answer(self, chosen: Chosen) -> BackendAnswer:
        probabilities = chosen.probabilities
        total = sum(probabilities.values())
        if total > 0 and abs(total - 1) <= RESCALE_WITHIN:
            probabilities = {option: value / total for option, value in probabilities.items()}
        return BackendAnswer(
            chosen.choice,
            probabilities,
            confidence=chosen.confidence,
            model=self._decisions.model_name,
        )


def _descriptions(question: str, options: list[str]) -> list[tuple[str, str]]:
    """When each option applies, read from the question's own lines ("- option: ...").
    An option the question does not explain is described by its name."""
    described = []
    for option in options:
        line = re.search(rf"^- {re.escape(option)}: (.+)$", question, re.MULTILINE)
        described.append((option, line.group(1).strip() if line else option))
    return described
