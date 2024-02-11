import datetime as dt
import hashlib
import itertools
from collections import OrderedDict
from collections.abc import Generator, Mapping
from pathlib import Path

import alive_progress as ap
import pandas as pd
from pandas import DataFrame

from bocoel.core.optim import Optimizer
from bocoel.corpora import Corpus, Embedder
from bocoel.models import Adaptor, ClassifierModel, GenerativeModel

from . import columns
from .examinators import Examinator


class Manager:
    """
    The manager for running and saving evaluations.
    """

    examinator: Examinator
    """
    The examinator that would perform evaluations on the results.
    """

    def __init__(self, path: str | Path | None = None) -> None:
        """
        Parameters:
            path: The path to save the scores to.

        Raises:
            ValueError: If the path is not a directory.
        """

        if path is not None:
            path = Path(path)
            if path.exists() and not path.is_dir():
                raise ValueError(f"{path} is not a directory")
            path.mkdir(parents=True, exist_ok=True)

        self.path = path
        self._start = self.current()
        self.examinator = Examinator.presets()

    def run(
        self, optimizer: Optimizer, corpus: Corpus, steps: int | None = None
    ) -> DataFrame:
        """
        Runs the optimizer until the end.

        Parameters:
            optimizer: The optimizer to run.
            corpus: The corpus to run the optimizer on.
            steps: The number of steps to run the optimizer for.

        Returns:
            The final state of the optimizer.
                Keys are the indices of the queries,
                and values are the corresponding scores.
        """

        results: OrderedDict[int, float] = OrderedDict()
        for res in self._launch(optimizer=optimizer, steps=steps):
            results.update(res)

        scores = self.examinator.examine(index=corpus.index, results=results)
        return scores

    def save(
        self,
        scores: DataFrame,
        optimizer: Optimizer,
        corpus: Corpus,
        model: GenerativeModel | ClassifierModel,
        adaptor: Adaptor,
        embedder: Embedder,
    ) -> None:
        """
        Saves the scores to the path.

        Parameters:
            scores: The scores to save.
            optimizer: The optimizer used to generate the scores.
            corpus: The corpus used to generate the scores.
            model: The model used to generate the scores.
            adaptor: The adaptor used to generate the scores.
            embedder: The embedder used to generate the scores.

        Raises:
            ValueError: If the path is not set.
        """

        md5, scores = self.with_identifier_cols(
            scores, optimizer, corpus, model, adaptor, embedder
        )

        if self.path is None:
            raise ValueError("No path specified. Set the path to save the scores.")

        scores.to_csv(self.path / f"{md5}.csv", index=False)

    def with_identifier_cols(
        self,
        df: DataFrame,
        optimizer: Optimizer,
        corpus: Corpus,
        model: GenerativeModel | ClassifierModel,
        adaptor: Adaptor,
        embedder: Embedder,
    ) -> tuple[str, DataFrame]:
        """
        Adds identifier columns to the DataFrame.

        Parameters:
            df: The DataFrame to add the columns to.
            optimizer: The optimizer used to generate the scores.
            corpus: The corpus used to generate the scores.
            model: The model used to generate the scores.
            adaptor: The adaptor used to generate the scores.
            embedder: The embedder used to generate the scores.

        Returns:
            The md5 hash of the identifier columns and the DataFrame with the columns added.
        """

        df = df.copy()

        md5 = self.md5(optimizer, corpus, model, adaptor, embedder, self._start)

        def assign(column: str, data: str) -> None:
            df[column] = [data] * len(df)

        assign(columns.OPTIMIZER, str(optimizer))
        assign(columns.MODEL, str(model))
        assign(columns.ADAPTOR, str(adaptor))
        assign(columns.INDEX, str(corpus.index.index))
        assign(columns.STORAGE, str(corpus.storage))
        assign(columns.EMBEDDER, str(embedder))
        assign(columns.TIME, self._start)
        assign(columns.MD5, md5)

        return md5, df

    @staticmethod
    def _launch(
        optimizer: Optimizer, steps: int | None = None
    ) -> Generator[Mapping[int, float], None, None]:
        "Launches the optimizer as a generator."

        steps_range = range(steps) if steps is not None else itertools.count()

        with ap.alive_bar(total=steps, title="optimizing") as bar:
            for _ in steps_range:
                bar()

                # Raises StopIteration (converted to RuntimError per PEP 479) if done.
                try:
                    results = optimizer.step()
                except StopIteration:
                    break

                yield results

    @staticmethod
    def load(path: str | Path) -> DataFrame:
        """
        Loads the scores from the path.

        Parameters:
            path: The path to load the scores from.

        Returns:
            The loaded scores.

        Raises:
            ValueError: If the path does not exist or is not a directory.
            ValueError: If no csv files are found in the path.
        """

        # Iterate over all csv files in the path.
        dfs = [pd.read_csv(csv) for csv in Path(path).glob("*.csv")]

        if not dfs:
            raise ValueError(f"No csv files found in {path}")

        return pd.concat(dfs)

    @staticmethod
    def md5(
        optimizer: Optimizer,
        corpus: Corpus,
        model: GenerativeModel | ClassifierModel,
        adaptor: Adaptor,
        embedder: Embedder,
        time: str,
    ) -> str:
        """
        Generates an md5 hash from the given data.

        Parameters:
            optimizer: The optimizer used to generate the scores.
            corpus: The corpus used to generate the scores.
            model: The model used to generate the scores.
            adaptor: The adaptor used to generate the scores.
            embedder: The embedder used to generate the scores.
            time: The time the scores were generated.

        Returns:
            The md5 hash of the given data.
        """

        data = [
            optimizer,
            embedder,
            corpus.index.index,
            corpus.storage,
            model,
            adaptor,
            time,
        ]

        return hashlib.md5(
            str.encode(" ".join([str(item) for item in data]))
        ).hexdigest()

    @staticmethod
    def current() -> str:
        return dt.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
