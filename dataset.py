"""
data generator for feeding data into pytorch models
"""

import os
import json
import time
import textwrap
from random import shuffle, sample
from copy import deepcopy
from typing import Optional, List, Tuple, Sequence, Set

import numpy as np

np.set_printoptions(precision=5, suppress=True)
from easydict import EasyDict as ED

try:
    from tqdm.auto import tqdm
except ModuleNotFoundError:
    from tqdm import tqdm
import torch
from torch.utils.data.dataset import Dataset

from helper_code import (  # noqa: F401
    load_recording,
    load_header,
    get_adc_gains,
    get_baselines,
)

from cfg import (  # noqa: F401
    TrainCfg,
    ModelCfg,
    TrainCfg_ns,
    ModelCfg_ns,
)
from data_reader import CINC2021Reader as CR
from utils.utils_signal import ensure_siglen
from utils.misc import list_sum
from signal_processing.ecg_denoise import remove_spikes_naive
from cfg import Standard12Leads

# from torch_ecg.torch_ecg._preprocessors import PreprocManager
from torch_ecg_bak.torch_ecg._preprocessors import PreprocManager


if ModelCfg.torch_dtype.lower() == "double":
    torch.set_default_tensor_type(torch.DoubleTensor)


__all__ = [
    "CINC2021",
]


_BASE_DIR = os.path.dirname(__file__)


class CINC2021(Dataset):
    """ """

    __DEBUG__ = False
    __name__ = "CINC2021"

    def __init__(self, config: ED, training: bool = True, lazy: bool = True) -> None:
        """finished, checked,

        Parameters
        ----------
        config: dict,
            configurations for the Dataset,
            ref. `cfg.TrainCfg`
        training: bool, default True,
            if True, the training set will be loaded, otherwise the test set
        lazy: bool, default True,
            if True, the data will not be loaded immediately,
        """
        super().__init__()
        self.config = deepcopy(config)
        self._TRANCHES = (
            self.config.tranche_classes.keys()
        )  # ["A", "B", "AB", "E", "F", "G",]
        self.reader = CR(db_dir=config.db_dir)
        self.tranches = config.tranches_for_training
        self.training = training
        if self.config.torch_dtype.lower() == "double":
            self.dtype = np.float64
        else:
            self.dtype = np.float32
        assert not self.tranches or self.tranches in self._TRANCHES
        if self.tranches:
            self.all_classes = self.config.tranche_classes[self.tranches]
            self.class_weights = self.config.tranche_class_weights[self.tranches]
        else:
            self.all_classes = self.config.classes
            self.class_weights = self.config.class_weights
        self.config.all_classes = deepcopy(self.all_classes)
        self.n_classes = len(self.all_classes)
        # print(f"tranches = {self.tranches}, all_classes = {self.all_classes}")
        # print(f"class_weights = {dict_to_str(self.class_weights)}")
        cw = np.zeros((len(self.class_weights),), dtype=self.dtype)
        for idx, c in enumerate(self.all_classes):
            cw[idx] = self.class_weights[c]
        self.class_weights = torch.from_numpy(cw.astype(self.dtype)).view(
            1, self.n_classes
        )
        # validation also goes in batches, hence length has to be fixed
        self.siglen = self.config.input_len
        self.lazy = lazy

        self._indices = [Standard12Leads.index(ld) for ld in self.config.leads]

        self.records = self._train_test_split(config.train_ratio, force_recompute=False)
        # TODO: consider using `remove_spikes_naive` to treat these exceptional records
        self.records = [
            r
            for r in self.records
            if r not in self.reader.exceptional_records
            and os.path.isfile(self.reader.get_data_filepath(r))
        ]
        if self.__DEBUG__:
            self.records = sample(self.records, int(len(self.records) * 0.01))

        ppm_config = ED(random=False)
        ppm_config.update(self.config)
        self.ppm = PreprocManager.from_config(ppm_config)
        self.ppm.rearrange(["bandpass", "normalize"])

        self._signals = np.array([], dtype=self.dtype).reshape(
            0, len(self.config.leads), self.siglen
        )
        self._labels = np.array([], dtype=self.dtype).reshape(0, self.n_classes)
        if not self.lazy:
            self._load_all_data()

    def _load_all_data(self) -> None:
        """ """
        # self.reader can not be pickled
        # with mp.Pool(processes=max(1, mp.cpu_count()-2)) as pool:
        #     self._signals, self._labels = \
        #         zip(*pool.starmap(_load_record, [(self.reader, r, self.config) for r in self.records]))

        # self._signals = np.array([]).reshape(0, len(self.config.leads), self.siglen)
        # self._labels = np.array([]).reshape(0, self.n_classes)

        fdr = FastDataReader(self.reader, self.records, self.config, self.ppm)

        # with tqdm(self.records, desc="Loading data", unit="records") as pbar:
        #     for rec in pbar:
        # sig, lb = self._load_one_record(rec)  # self._load_one_record is much slower than FastDataReader
        self._signals, self._labels = [], []
        with tqdm(range(len(fdr)), desc="Loading data", unit="records") as pbar:
            for idx in pbar:
                sig, lb = fdr[idx]
                # np.concatenate slows down the process severely
                # self._signals = np.concatenate((self._signals, sig), axis=0)
                # self._labels = np.concatenate((self._labels, lb), axis=0)
                self._signals.append(sig)
                self._labels.append(lb)
        self._signals = np.concatenate(self._signals, axis=0).astype(self.dtype)
        self._labels = np.concatenate(self._labels, axis=0)

    def _load_one_record(self, rec: str) -> Tuple[np.ndarray, np.ndarray]:
        """finished, checked,

        load a record from the database using data reader

        NOTE
        ----
        DO NOT USE THIS FUNCTION DIRECTLY for preloading data,
        use `FastDataReader` instead

        Parameters
        ----------
        rec: str,
            the record to load

        Returns
        -------
        values: np.ndarray,
            the values of the record
        labels: np.ndarray,
            the labels of the record
        """
        values = self.reader.load_resampled_data(
            rec,
            leads=self.config.leads,
            # leads=Standard12Leads,
            data_format=self.config.data_format,
            siglen=None,
        )
        for ld in range(values.shape[0]):
            values[ld] = remove_spikes_naive(values[ld])
        values, _ = self.ppm(values, self.config.fs)
        values = ensure_siglen(
            values,
            siglen=self.siglen,
            fmt=self.config.data_format,
            tolerance=self.config.sig_slice_tol,
        ).astype(self.dtype)
        if values.ndim == 2:
            values = values[np.newaxis, ...]

        labels = self.reader.get_labels(rec, scored_only=True, fmt="a", normalize=True)
        labels = (
            np.isin(self.all_classes, labels)
            .astype(self.dtype)[np.newaxis, ...]
            .repeat(values.shape[0], axis=0)
        )

        return values, labels

    def to(self, leads: Sequence[str]) -> None:
        """ """
        prev_leads = self.config.leads
        self.config.leads = leads
        self._indices = [prev_leads.index(ld) for ld in leads]
        self._signals = self._signals[:, self._indices, :]

    def emtpy(self, leads: Optional[Sequence[str]] = None) -> None:
        """ """
        if leads is None:
            leads = self.config.leads
        else:
            self.config.leads = leads
        self._signals = np.array([], dtype=self.dtype).reshape(
            0, len(leads), self.siglen
        )

    @classmethod
    def from_extern(cls, ext_ds: "CINC2021", config: ED) -> "CINC2021":
        """ """
        new_ds = cls(config, ext_ds.training, lazy=True)
        indices = [ext_ds.config.leads.index(ld) for ld in new_ds.config.leads]
        new_ds._signals = ext_ds._signals[:, indices, :]
        new_ds._labels = ext_ds._labels.copy()
        return new_ds

    def reload_from_extern(self, ext_ds: "CINC2021") -> None:
        """ """
        indices = [ext_ds.config.leads.index(ld) for ld in self.config.leads]
        self._signals = ext_ds._signals[:, indices, :]
        self._labels = ext_ds._labels.copy()

    @property
    def signals(self) -> np.ndarray:
        """ """
        return self._signals

    @property
    def labels(self) -> np.ndarray:
        """ """
        return self._labels

    def __getitem__(self, index: int) -> Tuple[np.ndarray, np.ndarray]:
        """finished, checked,"""
        return self.signals[index], self.labels[index]

    def __len__(self) -> int:
        """ """
        return len(self._signals)

    def _train_test_split(
        self, train_ratio: float = 0.8, force_recompute: bool = False
    ) -> List[str]:
        """finished, checked,

        do train test split,
        it is ensured that both the train and the test set contain all classes

        Parameters
        ----------
        train_ratio: float, default 0.8,
            ratio of the train set in the whole dataset (or the whole tranche(s))
        force_recompute: bool, default False,
            if True, force redo the train-test split,
            regardless of the existing ones stored in json files

        Returns
        -------
        records: list of str,
            list of the records split for training or validation
        """
        time.sleep(1)
        start = time.time()
        print("\nstart performing train test split...\n")
        time.sleep(1)
        _TRANCHES = list("ABEFG")
        _train_ratio = int(train_ratio * 100)
        _test_ratio = 100 - _train_ratio
        assert _train_ratio * _test_ratio > 0

        ns = "_ns" if len(self.config.special_classes) == 0 else ""
        file_suffix = f"_siglen_{self.siglen}{ns}.json"
        train_file = os.path.join(
            self.reader.db_dir_base, f"train_ratio_{_train_ratio}{file_suffix}"
        )
        test_file = os.path.join(
            self.reader.db_dir_base, f"test_ratio_{_test_ratio}{file_suffix}"
        )

        if not all([os.path.isfile(train_file), os.path.isfile(test_file)]):
            train_file = os.path.join(
                _BASE_DIR, "utils", f"train_ratio_{_train_ratio}{file_suffix}"
            )
            test_file = os.path.join(
                _BASE_DIR, "utils", f"test_ratio_{_test_ratio}{file_suffix}"
            )

        # TODO: use self.reader.df_stats (precomputed and stored in utils/stats.csv)
        # to accelerate the validity examinations
        if force_recompute or not all(
            [os.path.isfile(train_file), os.path.isfile(test_file)]
        ):
            tranche_records = {t: [] for t in _TRANCHES}
            train_set = {t: [] for t in _TRANCHES}
            test_set = {t: [] for t in _TRANCHES}
            for t in _TRANCHES:
                with tqdm(
                    self.reader.all_records[t], total=len(self.reader.all_records[t])
                ) as bar:
                    for rec in bar:
                        if rec in self.reader.exceptional_records:
                            # skip exceptional records
                            continue
                        rec_labels = self.reader.get_labels(
                            rec, scored_only=True, fmt="a", normalize=True
                        )
                        rec_labels = [
                            c for c in rec_labels if c in self.config.tranche_classes[t]
                        ]
                        if len(rec_labels) == 0:
                            # skip records with no scored class
                            continue
                        rec_samples = self.reader.load_resampled_data(rec).shape[1]
                        # NEW in CinC2021 compared to CinC2020
                        # training input siglen raised from 4000 to 5000,
                        # hence allow tolerance in siglen now
                        if rec_samples < self.siglen - self.config.input_len_tol:
                            continue
                        tranche_records[t].append(rec)
                time.sleep(1)
                print(
                    f"tranche {t} has {len(tranche_records[t])} valid records for training"
                )
            for t in _TRANCHES:
                is_valid = False
                while not is_valid:
                    shuffle(tranche_records[t])
                    split_idx = int(len(tranche_records[t]) * train_ratio)
                    train_set[t] = tranche_records[t][:split_idx]
                    test_set[t] = tranche_records[t][split_idx:]
                    is_valid = self._check_train_test_split_validity(
                        train_set[t], test_set[t], set(self.config.tranche_classes[t])
                    )
            train_file_1 = os.path.join(
                self.reader.db_dir_base, f"train_ratio_{_train_ratio}{file_suffix}"
            )
            train_file_2 = os.path.join(
                _BASE_DIR, "utils", f"train_ratio_{_train_ratio}{file_suffix}"
            )
            with open(train_file_1, "w") as f1, open(train_file_2, "w") as f2:
                json.dump(train_set, f1, ensure_ascii=False)
                json.dump(train_set, f2, ensure_ascii=False)
            test_file_1 = os.path.join(
                self.reader.db_dir_base, f"test_ratio_{_test_ratio}{file_suffix}"
            )
            test_file_2 = os.path.join(
                _BASE_DIR, "utils", f"test_ratio_{_test_ratio}{file_suffix}"
            )
            with open(test_file_1, "w") as f1, open(test_file_2, "w") as f2:
                json.dump(test_set, f1, ensure_ascii=False)
                json.dump(test_set, f2, ensure_ascii=False)
            print(
                textwrap.dedent(
                    f"""
                train set saved to \n\042{train_file_1}\042and\n\042{train_file_2}\042
                test set saved to \n\042{test_file_1}\042and\n\042{test_file_2}\042
                """
                )
            )
        else:
            with open(train_file, "r") as f:
                train_set = json.load(f)
            with open(test_file, "r") as f:
                test_set = json.load(f)

        print(f"train test split finished in {(time.time()-start)/60:.2f} minutes")

        _tranches = list(self.tranches or "ABEFG")
        if self.training == "all":
            records = list_sum([train_set[k] for k in _tranches]) + list_sum(
                [test_set[k] for k in _tranches]
            )
        elif self.training is True:
            records = list_sum([train_set[k] for k in _tranches])
        else:
            records = list_sum([test_set[k] for k in _tranches])
        return records

    def _check_train_test_split_validity(
        self, train_set: List[str], test_set: List[str], all_classes: Set[str]
    ) -> bool:
        """finished, checked,

        the train-test split is valid iff
        records in both `train_set` and `test` contain all classes in `all_classes`

        Parameters
        ----------
        train_set: list of str,
            list of the records in the train set
        test_set: list of str,
            list of the records in the test set
        all_classes: set of str,
            the set of all classes for training

        Returns
        -------
        is_valid: bool,
            the split is valid or not
        """
        train_classes = set(
            list_sum([self.reader.get_labels(rec, fmt="a") for rec in train_set])
        )
        train_classes.intersection_update(all_classes)
        test_classes = set(
            list_sum([self.reader.get_labels(rec, fmt="a") for rec in test_set])
        )
        test_classes.intersection_update(all_classes)
        is_valid = len(all_classes) == len(train_classes) == len(test_classes)
        print(
            textwrap.dedent(
                f"""
            all_classes:     {all_classes}
            train_classes:   {train_classes}
            test_classes:    {test_classes}
            is_valid:        {is_valid}
            """
            )
        )
        return is_valid

    def persistence(self) -> None:
        """finished, checked,

        make the dataset persistent w.r.t. the tranches and the ratios in `self.config`
        """
        _TRANCHES = "ABEFG"
        if self.training:
            ratio = int(self.config.train_ratio * 100)
        else:
            ratio = 100 - int(self.config.train_ratio * 100)
        fn_suffix = f"tranches_{self.tranches or _TRANCHES}_ratio_{ratio}"
        if self.config.bandpass is not None:
            bp_low = max(0, self.config.bandpass[0])
            bp_high = min(self.config.bandpass[1], self.config.fs // 2)
            fn_suffix = fn_suffix + f"_bp_{bp_low:.1f}_{bp_high:.1f}"
        fn_suffix = fn_suffix + f"_siglen_{self.siglen}"

        X, y = [], []
        with tqdm(range(self.__len__()), total=self.__len__()) as bar:
            for idx in bar:
                values, labels = self.__getitem__(idx)
                X.append(values)
                y.append(labels)
        X, y = np.array(X), np.array(y)
        print(f"X.shape = {X.shape}, y.shape = {y.shape}")
        filename = f"{'train' if self.training else 'test'}_X_{fn_suffix}.npy"
        np.save(os.path.join(self.reader.db_dir_base, filename), X)
        print(f"X saved to {filename}")
        filename = f"{'train' if self.training else 'test'}_y_{fn_suffix}.npy"
        np.save(os.path.join(self.reader.db_dir_base, filename), y)
        print(f"y saved to {filename}")

    def _check_nan(self) -> None:
        """finished, checked,

        during training, sometimes nan values are encountered,
        which ruins the whole training process
        """
        for idx, (values, labels) in enumerate(self):
            if np.isnan(values).any():
                print(f"values of {self.records[idx]} have nan values")
            if np.isnan(labels).any():
                print(f"labels of {self.records[idx]} have nan values")


class FastDataReader(Dataset):
    """ """

    def __init__(
        self,
        reader: CR,
        records: Sequence[str],
        config: ED,
        ppm: Optional[PreprocManager] = None,
    ) -> None:
        """ """
        self.reader = reader
        self.records = records
        self.config = config
        self.ppm = ppm
        if self.config.torch_dtype.lower() == "double":
            self.dtype = np.float64
        else:
            self.dtype = np.float32

    def __len__(self) -> int:
        """ """
        return len(self.records)

    def __getitem__(self, index: int) -> Tuple[np.ndarray, np.ndarray]:
        """ """
        rec = self.records[index]
        values = self.reader.load_resampled_data(
            rec,
            leads=self.config.leads,
            # leads=Standard12Leads,
            data_format=self.config.data_format,
            siglen=None,
        )
        for ld in range(values.shape[0]):
            values[ld] = remove_spikes_naive(values[ld])
        if self.ppm:
            values, _ = self.ppm(values, self.config.fs)
        values = ensure_siglen(
            values,
            siglen=self.config.input_len,
            fmt=self.config.data_format,
            tolerance=self.config.sig_slice_tol,
        ).astype(self.dtype)
        if values.ndim == 2:
            values = values[np.newaxis, ...]

        labels = self.reader.get_labels(rec, scored_only=True, fmt="a", normalize=True)
        labels = (
            np.isin(self.config.all_classes, labels)
            .astype(self.dtype)[np.newaxis, ...]
            .repeat(values.shape[0], axis=0)
        )

        return values, labels


def _load_record(reader: CR, rec: str, config: ED) -> Tuple[np.ndarray, np.ndarray]:
    """finished, NOT checked,

    load a record from the database using data reader

    Parameters
    ----------
    reader: CR,
        the data reader
    rec: str,
        the record to load
    config: dict,
        the configuration for loading record

    Returns
    -------
    values: np.ndarray,
        the values of the record
    labels: np.ndarray,
        the labels of the record
    """
    values = reader.load_resampled_data(
        rec, leads=config.leads, data_format="channel_first", siglen=None
    )
    values = ensure_siglen(values, siglen=config.input_len, fmt="channel_first")

    labels = reader.get_labels(rec, scored_only=True, fmt="a", normalize=True)
    labels = np.isin(config.all_classes, labels).astype(int)

    if config.data_format.lower() in ["channel_last", "lead_last"]:
        values = values.T

    return values, labels
