"""Backend A: a general language model with constrained output.

Its probabilities are the model's own estimate and are not calibrated.
"""

from typing import TYPE_CHECKING, Any, Literal

from pydantic import create_model

from thenwhat.decide.core import BackendAnswer, rescaled

if TYPE_CHECKING:
    from thenwhat.llm.client import Llm

INSTRUCTIONS = """\
You make one bounded classification. Choose exactly one of the options offered.
Also give your probability for every option, as numbers from 0 to 1 that sum to 1.
Judge only from the information given. Do not add outside knowledge about the subject.
"""
BATCH_INSTRUCTIONS = """\
You make the same bounded classification for each numbered item. Give one answer per
item, with the item's number. For each, choose exactly one of the options offered and
give your probability for every option, as numbers from 0 to 1 that sum to 1.
Judge each item on its own, only from the information given about it. Do not add
outside knowledge about the subject.
"""


class LlmBackend:
    name = "llm"

    def __init__(self, llm: "Llm") -> None:
        self._llm = llm

    def answer(self, step: str, state: str, options: list[str]) -> BackendAnswer:
        # The model may only return one of the options: built at run time, so not a static type.
        one_of_the_options: Any = Literal.__getitem__(tuple(options))
        shape = create_model(
            "Choice",
            choice=(one_of_the_options, ...),
            probabilities=(dict[str, float], ...),
        )
        result = self._llm.run(
            f"decision:{step}",
            instructions=INSTRUCTIONS,
            prompt=f"{state}\n\nOptions: {', '.join(options)}",
            output_type=shape,
        )
        return self._as_answer(
            result.choice,  # ty: ignore[missing-attribute]
            result.probabilities,  # ty: ignore[missing-attribute]
        )

    def answer_many(
        self, step: str, intro: str, question: str, items: list[str], options: list[str]
    ) -> list[BackendAnswer | None]:
        """One model call for all the items. An item the model leaves out is asked alone."""
        one_of_the_options: Any = Literal.__getitem__(tuple(options))
        item_shape = create_model(
            "ItemChoice",
            item=(int, ...),
            choice=(one_of_the_options, ...),
            probabilities=(dict[str, float], ...),
        )
        many: Any = list.__class_getitem__(item_shape)
        shape = create_model("Choices", answers=(many, ...))
        numbered = "\n\n".join(f"[{number}] {text}" for number, text in enumerate(items, 1))
        result = self._llm.run(
            f"decision:{step}",
            instructions=BATCH_INSTRUCTIONS,
            prompt=(
                f"{intro}\n\n{question}\n\nOptions: {', '.join(options)}\n\nItems:\n\n{numbered}"
            ),
            output_type=shape,
        )
        given = {given.item: given for given in result.answers}  # ty: ignore[missing-attribute]
        answers: list[BackendAnswer | None] = []
        for number, text in enumerate(items, 1):
            one = given.get(number)
            if one is None:
                answers.append(self.answer(step, f"{intro}\n\n{text}\n\n{question}", options))
            else:
                answers.append(self._as_answer(one.choice, one.probabilities))
        return answers

    def _as_answer(self, choice: str, probabilities: dict[str, float]) -> BackendAnswer:
        return BackendAnswer(choice, rescaled(probabilities), model=self._llm.model_name)
