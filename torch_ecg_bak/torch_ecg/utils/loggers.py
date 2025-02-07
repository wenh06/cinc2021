"""
loggers, including (planned) CSVLogger, TensorBoardXLogger, WandbLogger

with reference to `loggers` of `textattack` and `loggers` of `pytorch-lightning`
"""

import os, logging, csv
from datetime import datetime
from abc import ABC, abstractmethod
from typing import NoReturn, Optional, Union, List, Any, Dict
from numbers import Real

import torch
import pandas as pd
import tensorboardX

from ..utils.misc import (
    get_date_str, default_class_repr, init_logger,
)
from ..cfg import DEFAULTS


__all__ = [
    "BaseLogger",
    "TxtLogger",
    "CSVLogger",
    "TensorBoardXLogger",
    "WandbLogger",
    "LoggerManager",
]


class BaseLogger(ABC):
    """
    the abstract base class of all loggers
    """
    __name__ = "BaseLogger"

    @abstractmethod
    def log_metrics(self,
                    metrics:Dict[str, Union[Real,torch.Tensor]],
                    step:Optional[int]=None,
                    epoch:Optional[int]=None,
                    part:str="train",) -> NoReturn:
        """

        Parameters
        ----------
        metrics: dict,
            the metrics to be logged
        step: int, optional,
            the number of (global) steps of training
        epoch: int, optional,
            the epoch number of training
        part: str, optional,
            the part of the training data the metrics computed from,
            can be "train" or "val" or "test", etc.
        """
        raise NotImplementedError

    @abstractmethod
    def log_message(self, msg:str, level:int=logging.INFO) -> NoReturn:
        """
        log a message

        Parameters
        ----------
        msg: str,
            the message to be logged
        level: int, optional,
            the level of the message,
            can be logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR, logging.CRITICAL
        """
        raise NotImplementedError

    @abstractmethod
    def flush(self) -> NoReturn:
        """
        """
        raise NotImplementedError

    @abstractmethod
    def close(self) -> NoReturn:
        """
        """
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def from_config(cls, config:Dict[str, Any]) -> Any:
        """
        """
        raise NotImplementedError

    def epoch_start(self, epoch:int) -> NoReturn:
        """
        actions to be performed at the start of each epoch

        Parameters
        ----------
        epoch: int,
            the number of the epoch
        """
        pass

    def epoch_end(self, epoch:int) -> NoReturn:
        """
        actions to be performed at the end of each epoch

        Parameters
        ----------
        epoch: int,
            the number of the epoch
        """
        pass

    @property
    def log_dir(self) -> str:
        """
        """
        return self._log_dir

    @property
    @abstractmethod
    def filename(self) -> str:
        """
        """
        raise NotImplementedError

    def __repr__(self) -> str:
        return default_class_repr(self)

    __str__ = __repr__

    def extra_repr_keys(self) -> List[str]:
        """
        extra keys to be displayed in the repr of the logger
        """
        return ["filename",]


class TxtLogger(BaseLogger):
    """
    """
    __name__ = "TxtLogger"

    def __init__(self, log_dir:Optional[str]=None, log_suffix:Optional[str]=None,) -> NoReturn:
        """

        Parameters
        ----------
        log_dir: str, optional,
            the directory to save the log file
        log_suffix: str, optional,
            the suffix of the log file
        """
        self._log_dir = log_dir or DEFAULTS.log_dir
        if log_suffix is None:
            log_suffix = ""
        else:
            log_suffix = f"_{log_suffix}"
        self.log_file = f"{DEFAULTS.prefix}_{get_date_str()}{log_suffix}.txt"
        self.logger = init_logger(self.log_dir, self.log_file, verbose=1)
        self.step = -1

    def log_metrics(self,
                    metrics:Dict[str, Union[Real,torch.Tensor]],
                    step:Optional[int]=None,
                    epoch:Optional[int]=None,
                    part:str="train",) -> NoReturn:
        """

        Parameters
        ----------
        metrics: dict,
            the metrics to be logged
        step: int, optional,
            the number of (global) steps of training
        epoch: int, optional,
            the epoch number of training
        part: str, optional,
            the part of the training data the metrics computed from,
            can be "train" or "val" or "test", etc.
        """
        if step is not None:
            self.step = step
        else:
            self.step += 1
        prefix = f"Step {step}: "
        if epoch is not None:
            prefix = f"Epoch {epoch} / {prefix}"
        _metrics = {k: v.item() if isinstance(v, torch.Tensor) else v for k,v in metrics.items()}
        spaces = len(max(_metrics.keys(), key=len))
        msg = f"{part.capitalize()} Metrics:\n{self.short_sep}\n" \
            + "\n".join([f"{prefix}{part}/{k} : {' '*(spaces-len(k))}{v:.4f}" for k,v in _metrics.items()]) \
            + f"\n{self.short_sep}"
        self.log_message(msg)

    def log_message(self, msg:str, level:int=logging.INFO) -> NoReturn:
        """
        log a message

        Parameters
        ----------
        msg: str,
            the message to be logged
        level: int, optional,
            the level of the message,
            can be logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR, logging.CRITICAL
        """
        self.logger.log(level, msg)

    @property
    def long_sep(self) -> str:
        """
        """
        return "-"*110

    @property
    def short_sep(self) -> str:
        """
        """
        return "-"*50

    def epoch_start(self, epoch:int) -> NoReturn:
        """
        message logged at the start of each epoch

        Parameters
        ----------
        epoch: int,
            the number of the epoch
        """
        self.logger.info(f"Train epoch_{epoch}:\n{self.long_sep}")

    def epoch_end(self, epoch:int) -> NoReturn:
        """
        message logged at the end of each epoch

        Parameters
        ----------
        epoch: int,
            the number of the epoch
        """
        self.logger.info(f"{self.long_sep}\n")

    def flush(self) -> NoReturn:
        """
        """
        for h in self.logger.handlers:
            if hasattr(h, flush):
                h.flush()

    def close(self) -> NoReturn:
        """
        """
        for h in self.logger.handlers:
            h.close()
            self.logger.removeHandler(h)
        logging.shutdown()

    @classmethod
    def from_config(cls, config:Dict[str, Any]) -> "TxtLogger":
        """
        """
        return cls(config.get("log_dir", None), config.get("log_suffix", None))

    @property
    def filename(self) -> str:
        """
        """
        return os.path.join(self.log_dir, self.log_file)


class CSVLogger(BaseLogger):
    """
    """
    __name__ = "CSVLogger"

    def __init__(self, log_dir:Optional[str]=None, log_suffix:Optional[str]=None,) -> NoReturn:
        """

        Parameters
        ----------
        log_dir: str, optional,
            the directory to save the log file
        log_suffix: str, optional,
            the suffix of the log file
        """
        self._log_dir = log_dir or DEFAULTS.log_dir
        if log_suffix is None:
            log_suffix = ""
        else:
            log_suffix = f"_{log_suffix}"
        self.log_file = f"{DEFAULTS.prefix}_{get_date_str()}{log_suffix}.csv"
        self.logger = pd.DataFrame()
        self.step = -1
        self._flushed = True

    def log_metrics(self,
                    metrics:Dict[str, Union[Real,torch.Tensor]],
                    step:Optional[int]=None,
                    epoch:Optional[int]=None,
                    part:str="train",) -> NoReturn:
        """

        Parameters
        ----------
        metrics: dict,
            the metrics to be logged
        step: int, optional,
            the number of (global) steps of training
        epoch: int, optional,
            the epoch number of training
        part: str, optional,
            the part of the training data the metrics computed from,
            can be "train" or "val" or "test", etc.
        """
        if step is not None:
            self.step = step
        else:
            self.step += 1
        row = {"step": self.step, "time": datetime.now(), "part": part}
        if epoch is not None:
            row.update({"epoch": epoch})
        row.update(
            {k: v.item() if isinstance(v, torch.Tensor) else v for k,v in metrics.items()}
        )
        self.logger = self.logger.append(row, ignore_index=True)
        self._flushed = False

    def log_message(self, msg:str, level:int=logging.INFO) -> NoReturn:
        pass

    def flush(self) -> NoReturn:
        """
        """
        if not self._flushed:
            self.logger.to_csv(self.filename, quoting=csv.QUOTE_NONNUMERIC, index=False)
            self._flushed = True

    def close(self) -> NoReturn:
        """
        """
        self.flush()

    def __del__(self):
        """
        """
        self.flush()
        del self

    @classmethod
    def from_config(cls, config:Dict[str, Any]) -> "TxtLogger":
        """
        """
        return cls(config.get("log_dir", None), config.get("log_suffix", None))

    @property
    def filename(self) -> str:
        """
        """
        return os.path.join(self.log_dir, self.log_file)


class TensorBoardXLogger(BaseLogger):
    """
    """
    __name__ = "TensorBoardXLogger"

    def __init__(self, log_dir:Optional[str]=None, log_suffix:Optional[str]=None,) -> NoReturn:
        """

        Parameters
        ----------
        log_dir: str, optional,
            the directory to save the log file
        log_suffix: str, optional,
            the suffix of the log file
        """
        self._log_dir = log_dir or DEFAULTS.log_dir
        self.logger = tensorboardX.SummaryWriter(log_dir, filename_suffix=log_suffix or "")
        self.log_file = self.logger.file_writer.event_writer._ev_writer._file_name
        self.step = -1

    def log_metrics(self,
                    metrics:Dict[str, Union[Real,torch.Tensor]],
                    step:Optional[int]=None,
                    epoch:Optional[int]=None,
                    part:str="train",) -> NoReturn:
        """

        Parameters
        ----------
        metrics: dict,
            the metrics to be logged
        step: int, optional,
            the number of (global) steps of training
        epoch: int, optional,
            the epoch number of training
        part: str, optional,
            the part of the training data the metrics computed from,
            can be "train" or "val" or "test", etc.
        """
        if step is not None:
            self.step = step
        else:
            self.step += 1
        for k,v in metrics.items():
            if isinstance(v, torch.Tensor):
                v = v.item()
            self.logger.add_scalar(f"{part}/{k}", v, self.step)

    def log_message(self, msg:str, level:int=logging.INFO) -> NoReturn:
        pass

    def flush(self) -> NoReturn:
        """
        """
        self.logger.flush()

    def close(self) -> NoReturn:
        """
        """
        self.logger.close()

    @classmethod
    def from_config(cls, config:Dict[str, Any]) -> "TxtLogger":
        """
        """
        return cls(config.get("log_dir", None), config.get("log_suffix", None))

    @property
    def filename(self) -> str:
        """
        """
        return os.path.join(self.log_dir, self.log_file)


class WandbLogger(BaseLogger):
    """
    """
    __name__ = "WandbLogger"

    def __init__(self, project:str) -> NoReturn:
        """
        """
        self._project = project
        raise NotImplementedError

    def log_metrics(self, metrics:Dict[str, float], step:Optional[int]=None) -> NoReturn:
        """
        """
        raise NotImplementedError

    def log_message(self, msg:str, level:int=logging.INFO) -> NoReturn:
        pass

    def flush(self) -> NoReturn:
        """
        """
        raise NotImplementedError

    def close(self) -> NoReturn:
        """
        """
        raise NotImplementedError

    @classmethod
    def from_config(cls, config:Dict[str, Any]) -> "WandbLogger":
        """
        """
        raise NotImplementedError

    @property
    def filename(self) -> str:
        """
        """
        raise NotImplementedError


class LoggerManager(object):
    """
    """
    __name__ = "LoggerManager"

    def __init__(self, log_dir:Optional[str]=None, log_suffix:Optional[str]=None,) -> NoReturn:
        """

        Parameters
        ----------
        log_dir: str, optional,
            the directory to save the log file
        log_suffix: str, optional,
            the suffix of the log file
        """
        self._log_dir = log_dir or DEFAULTS.log_dir
        self._log_suffix = log_suffix
        self._loggers = []

    def _add_txt_logger(self) -> NoReturn:
        """
        """
        self.loggers.append(TxtLogger(self._log_dir, self._log_suffix))
    
    def _add_csv_logger(self) -> NoReturn:
        """
        """
        self.loggers.append(CSVLogger(self._log_dir, self._log_suffix))

    def _add_tensorboardx_logger(self) -> NoReturn:
        """
        """
        self.loggers.append(TensorBoardXLogger(self._log_dir, self._log_suffix))

    def _add_wandb_logger(self) -> NoReturn:
        """
        """
        raise NotImplementedError

    def log_metrics(self,
                    metrics:Dict[str, Union[Real,torch.Tensor]],
                    step:Optional[int]=None,
                    epoch:Optional[int]=None,
                    part:str="train",) -> NoReturn:
        """

        Parameters
        ----------
        metrics: dict,
            the metrics to be logged
        step: int, optional,
            the number of (global) steps of training
        epoch: int, optional,
            the epoch number of training
        part: str, optional,
            the part of the training data the metrics computed from,
            can be "train" or "val" or "test", etc.
        """
        for l in self.loggers:
            l.log_metrics(metrics, step, epoch, part)

    def log_message(self, msg:str, level:int=logging.INFO) -> NoReturn:
        """
        log a message

        Parameters
        ----------
        msg: str,
            the message to be logged
        level: int, optional,
            the level of the message,
            can be logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR, logging.CRITICAL
        """
        for l in self.loggers:
            l.log_message(msg, level)

    def epoch_start(self, epoch:int) -> NoReturn:
        """
        action at the start of an epoch

        Parameters
        ----------
        epoch: int,
            the epoch number
        """
        for l in self.loggers:
            l.epoch_start(epoch)

    def epoch_end(self, epoch:int) -> NoReturn:
        """
        action at the end of an epoch

        Parameters
        ----------
        epoch: int,
            the epoch number
        """
        for l in self.loggers:
            l.epoch_end(epoch)

    def flush(self) -> NoReturn:
        """
        """
        for l in self.loggers:
            l.flush()

    def close(self) -> NoReturn:
        """
        """
        for l in self.loggers:
            l.close()

    @property
    def loggers(self) -> List[BaseLogger]:
        """
        """
        return self._loggers

    @property
    def log_dir(self) -> str:
        """
        """
        return self._log_dir

    @property
    def log_suffix(self) -> str:
        """
        """
        return self._log_suffix

    @classmethod
    def from_config(cls, config:Dict[str, Any]) -> "LoggerManager":
        """

        Parameters
        ----------
        config: dict,
            the configuration of the logger manager

        Returns
        -------
        LoggerManager
        """
        lm =  cls(config.get("log_dir", None), config.get("log_suffix", None))
        if config.get("txt_logger", True):
            lm._add_txt_logger()
        if config.get("csv_logger", True):
            lm._add_csv_logger()
        if config.get("tensorboardx_logger", True):
            lm._add_tensorboardx_logger()
        if config.get("wandb_logger", False):
            lm._add_wandb_logger()
        return lm

    def __repr__(self) -> str:
        return default_class_repr(self)

    __str__ = __repr__

    def extra_repr_keys(self) -> List[str]:
        """
        extra keys to be displayed in the repr of the logger
        """
        return ["loggers",]
