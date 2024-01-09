import typing
from collections.abc import Sequence

from nltk.translate import bleu_score

from bocoel.models.scores.interfaces import LanguageModel

from .comparisons import CmpScore


class BleuScore(CmpScore):
    def __init__(self, problem: str, answer: str, lm: LanguageModel) -> None:
        self._problem = problem
        self._answer = answer
        self._lm = lm

    # TODO: Improve performance.
    def compare(
        self, generated: Sequence[str], reference: Sequence[str]
    ) -> Sequence[float]:
        return [
            typing.cast(float, bleu_score.sentence_bleu([ans.split()], gen.split()))
            for ans, gen in zip(reference, generated)
        ]
