from typing import Any

from bocoel import ComposedCorpus, Corpus, Embedder, Storage
from bocoel.common import StrEnum

from . import common, indices
from .indices import IndexName


class CorpusName(StrEnum):
    """
    The names of the corpus.
    """

    COMPOSED = "COMPOSED"
    "Corresponds to `ComposedCorpus`."


def corpus(
    name: str | CorpusName = CorpusName.COMPOSED,
    /,
    *,
    storage: Storage,
    embedder: Embedder,
    index_name: str | IndexName,
    **index_kwargs: Any,
) -> Corpus:
    """
    Create a corpus.

    Parameters:
        name: The name of the corpus.
        storage: The storage to use.
        embedder: The embedder to use.
        index_name: The name of the index backend to use.
        **index_kwargs: The keyword arguments to pass to the index backend.

    Returns:
        The corpus instance.

    Raises:
        ValueError: If the name is unknown.
    """

    if CorpusName.lookup(name) is not CorpusName.COMPOSED:
        raise ValueError(f"Unknown corpus name: {name}")

    return common.correct_kwargs(ComposedCorpus.index_storage)(
        storage=storage,
        embedder=embedder,
        index_backend=indices.index_class(index_name),
        **indices.index_set_backends(index_kwargs),
    )
