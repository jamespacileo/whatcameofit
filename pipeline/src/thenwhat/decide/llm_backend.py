"""Backend A: a general language model with constrained output.

Its probabilities are the model's own estimate and are not calibrated.
"""

from typing import TYPE_CHECKING, Any, Literal

from pydantic import create_model

from thenwhat.decide.core import BackendAnswer

if TYPE_CHECKING:
    from thenwhat.llm.client import Llm

INSTRUCTIONS = """\
You make one bounded classification. Choose exactly one of the options offered.
Also give your probability for every option, as numbers from 0 to 1 that sum to 1.
Judge only from the information given. Do not add outside knowledge about the subject.
"""
# Models often return probabilities that sum to 0.98 or 1.01; that much is rescaled.
RESCALE_WITHIN = 0.1


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
        probabilities: dict[str, float] = result.probabilities  # ty: ignore[missing-attribute]
        total = sum(probabilities.values())
        if total > 0 and abs(total - 1) <= RESCALE_WITHIN:
            probabilities = {option: value / total for option, value in probabilities.items()}
        return BackendAnswer(
            result.choice,  # ty: ignore[missing-attribute]
            probabilities,
            model=self._llm.model_name,
        )
