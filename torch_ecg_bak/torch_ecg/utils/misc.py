"""
"""
import os, sys
import re
import logging
import datetime
from functools import reduce
from collections import namedtuple
from glob import glob
from copy import deepcopy
from typing import Union, Optional, List, Dict, Tuple, Sequence, NoReturn, Any
from numbers import Real, Number

import numpy as np
np.set_printoptions(precision=5, suppress=True)
from scipy import interpolate
from sklearn.utils import compute_class_weight
from wfdb.io import _header
from wfdb import Record, MultiRecord
from easydict import EasyDict as ED



__all__ = [
    "get_record_list_recursive",
    "get_record_list_recursive2",
    "get_record_list_recursive3",
    "dict_to_str",
    "str2bool",
    "diff_with_step",
    "ms2samples",
    "samples2ms",
    "get_mask",
    "class_weight_to_sample_weight",
    "plot_single_lead",
    "init_logger",
    "get_date_str",
    "rdheader",
    "ensure_lead_fmt", "ensure_siglen",
    "ECGWaveForm", "masks_to_waveforms",
    "list_sum",
]


def get_record_list_recursive(db_dir:str, rec_ext:str) -> List[str]:
    """ finished, checked,

    get the list of records in `db_dir` recursively,
    for example, there are two folders "patient1", "patient2" in `db_dir`,
    and there are records "A0001", "A0002", ... in "patient1"; "B0001", "B0002", ... in "patient2",
    then the output would be "patient1{sep}A0001", ..., "patient2{sep}B0001", ...,
    sep is determined by the system

    Parameters:
    -----------
    db_dir: str,
        the parent (root) path of the whole database
    rec_ext: str,
        extension of the record files

    Returns:
    --------
    res: list of str,
        list of records, in lexicographical order
    """
    res = []
    db_dir = os.path.join(db_dir, "tmp").replace("tmp", "")  # make sure `db_dir` ends with a sep
    roots = [db_dir]
    while len(roots) > 0:
        new_roots = []
        for r in roots:
            tmp = [os.path.join(r, item) for item in os.listdir(r)]
            res += [item for item in tmp if os.path.isfile(item)]
            new_roots += [item for item in tmp if os.path.isdir(item)]
        roots = deepcopy(new_roots)
    res = [os.path.splitext(item)[0].replace(db_dir, "") for item in res if item.endswith(rec_ext)]
    res = sorted(res)

    return res


def get_record_list_recursive2(db_dir:str, rec_pattern:str) -> List[str]:
    """ finished, checked,

    get the list of records in `db_dir` recursively,
    for example, there are two folders "patient1", "patient2" in `db_dir`,
    and there are records "A0001", "A0002", ... in "patient1"; "B0001", "B0002", ... in "patient2",
    then the output would be "patient1{sep}A0001", ..., "patient2{sep}B0001", ...,
    sep is determined by the system

    Parameters:
    -----------
    db_dir: str,
        the parent (root) path of the whole database
    rec_pattern: str,
        pattern of the record filenames, e.g. "A*.mat"

    Returns:
    --------
    res: list of str,
        list of records, in lexicographical order
    """
    res = []
    db_dir = os.path.join(db_dir, "tmp").replace("tmp", "")  # make sure `db_dir` ends with a sep
    roots = [db_dir]
    while len(roots) > 0:
        new_roots = []
        for r in roots:
            tmp = [os.path.join(r, item) for item in os.listdir(r)]
            # res += [item for item in tmp if os.path.isfile(item)]
            res += glob(os.path.join(r, rec_pattern), recursive=False)
            new_roots += [item for item in tmp if os.path.isdir(item)]
        roots = deepcopy(new_roots)
    res = [os.path.splitext(item)[0].replace(db_dir, "") for item in res]
    res = sorted(res)

    return res


def get_record_list_recursive3(db_dir:str, rec_patterns:Union[str,Dict[str,str]]) -> Union[List[str], Dict[str, List[str]]]:
    """ finished, checked,

    get the list of records in `db_dir` recursively,
    for example, there are two folders "patient1", "patient2" in `db_dir`,
    and there are records "A0001", "A0002", ... in "patient1"; "B0001", "B0002", ... in "patient2",
    then the output would be "patient1{sep}A0001", ..., "patient2{sep}B0001", ...,
    sep is determined by the system

    Parameters:
    -----------
    db_dir: str,
        the parent (root) path of the whole database
    rec_patterns: str or dict,
        pattern of the record filenames, e.g. "A(?:\d+).mat",
        or patterns of several subsets, e.g. `{"A": "A(?:\d+).mat"}`

    Returns:
    --------
    res: list of str,
        list of records, in lexicographical order
    """
    if isinstance(rec_patterns, str):
        res = []
    elif isinstance(rec_patterns, dict):
        res = {k:[] for k in rec_patterns.keys()}
    db_dir = os.path.join(db_dir, "tmp").replace("tmp", "")  # make sure `db_dir` ends with a sep
    roots = [db_dir]
    while len(roots) > 0:
        new_roots = []
        for r in roots:
            tmp = [os.path.join(r, item) for item in os.listdir(r)]
            # res += [item for item in tmp if os.path.isfile(item)]
            if isinstance(rec_patterns, str):
                res += list(filter(re.compile(rec_patterns).search, tmp))
            elif isinstance(rec_patterns, dict):
                for k in rec_patterns.keys():
                    res[k] += list(filter(re.compile(rec_patterns[k]).search, tmp))
            new_roots += [item for item in tmp if os.path.isdir(item)]
        roots = deepcopy(new_roots)
    if isinstance(rec_patterns, str):
        res = [os.path.splitext(item)[0].replace(db_dir, "") for item in res]
        res = sorted(res)
    elif isinstance(rec_patterns, dict):
        for k in rec_patterns.keys():
            res[k] = [os.path.splitext(item)[0].replace(db_dir, "") for item in res[k]]
            res[k] = sorted(res[k])
    return res


def dict_to_str(d:Union[dict, list, tuple], current_depth:int=1, indent_spaces:int=4) -> str:
    """ finished, checked,

    convert a (possibly) nested dict into a `str` of json-like formatted form,
    this nested dict might also contain lists or tuples of dict (and of str, int, etc.)

    Parameters:
    -----------
    d: dict, or list, or tuple,
        a (possibly) nested `dict`, or a list of `dict`
    current_depth: int, default 1,
        depth of `d` in the (possible) parent `dict` or `list`
    indent_spaces: int, default 4,
        the indent spaces of each depth

    Returns:
    --------
    s: str,
        the formatted string
    """
    assert isinstance(d, (dict, list, tuple))
    if len(d) == 0:
        s = f"{{}}" if isinstance(d, dict) else f"[]"
        return s
    # flat_types = (Number, bool, str,)
    flat_types = (Number, bool,)
    flat_sep = ", "
    s = "\n"
    unit_indent = " "*indent_spaces
    prefix = unit_indent*current_depth
    if isinstance(d, (list, tuple)):
        if all([isinstance(v, flat_types) for v in d]):
            len_per_line = 110
            current_len = len(prefix) + 1  # + 1 for a comma 
            val = []
            for idx, v in enumerate(d):
                add_v = f"\042{v}\042" if isinstance(v, str) else str(v)
                add_len = len(add_v) + len(flat_sep)
                if current_len + add_len > len_per_line:
                    val = ", ".join([item for item in val])
                    s += f"{prefix}{val},\n"
                    val = [add_v]
                    current_len = len(prefix) + 1 + len(add_v)
                else:
                    val.append(add_v)
                    current_len += add_len
            if len(val) > 0:
                val = ", ".join([item for item in val])
                s += f"{prefix}{val}\n"
        else:
            for idx, v in enumerate(d):
                if isinstance(v, (dict, list, tuple)):
                    s += f"{prefix}{dict_to_str(v, current_depth+1)}"
                else:
                    val = f"\042{v}\042" if isinstance(v, str) else v
                    s += f"{prefix}{val}"
                if idx < len(d) - 1:
                    s += ",\n"
                else:
                    s += "\n"
    elif isinstance(d, dict):
        for idx, (k, v) in enumerate(d.items()):
            key = f"\042{k}\042" if isinstance(k, str) else k
            if isinstance(v, (dict, list, tuple)):
                s += f"{prefix}{key}: {dict_to_str(v, current_depth+1)}"
            else:
                val = f"\042{v}\042" if isinstance(v, str) else v
                s += f"{prefix}{key}: {val}"
            if idx < len(d) - 1:
                s += ",\n"
            else:
                s += "\n"
    s += unit_indent*(current_depth-1)
    s = f"{{{s}}}" if isinstance(d, dict) else f"[{s}]"
    return s


def str2bool(v:Union[str, bool]) -> bool:
    """ finished, checked,

    converts a "boolean" value possibly in the format of str to bool

    Parameters:
    -----------
    v: str or bool,
        the "boolean" value

    Returns:
    --------
    b: bool,
        `v` in the format of bool

    References:
    -----------
    https://stackoverflow.com/questions/15008758/parsing-boolean-values-with-argparse
    """
    if isinstance(v, bool):
       b = v
    elif v.lower() in ("yes", "true", "t", "y", "1"):
        b = True
    elif v.lower() in ("no", "false", "f", "n", "0"):
        b = False
    else:
        raise ValueError("Boolean value expected.")
    return b


def diff_with_step(a:np.ndarray, step:int=1, **kwargs) -> np.ndarray:
    """ finished, checked,

    compute a[n+step] - a[n] for all valid n

    Parameters:
    -----------
    a: ndarray,
        the input data
    step: int, default 1,
        the step to compute the difference
    kwargs: dict,

    Returns:
    --------
    d: ndarray:
        the difference array
    """
    if step >= len(a):
        raise ValueError(f"step ({step}) should be less than the length ({len(a)}) of `a`")
    d = a[step:] - a[:-step]
    return d


def ms2samples(t:Real, fs:Real) -> int:
    """ finished, checked,

    convert time `t` with units in ms to number of samples

    Parameters:
    -----------
    t: real number,
        time with units in ms
    fs: real number,
        sampling frequency of a signal

    Returns:
    --------
    n_samples: int,
        number of samples corresponding to time `t`
    """
    n_samples = t * fs // 1000
    return n_samples


def samples2ms(n_samples:int, fs:Real) -> Real:
    """ finished, checked,

    inverse function of `ms2samples`

    Parameters:
    -----------
    n_samples: int,
        number of sample points
    fs: real number,
        sampling frequency of a signal

    Returns:
    --------
    t: real number,
        time duration correponding to `n_samples`
    """
    t = n_samples * 1000 / fs
    return t


def get_mask(shape:Union[int, Sequence[int]], critical_points:np.ndarray, left_bias:int, right_bias:int, return_fmt:str="mask") -> Union[np.ndarray,list]:
    """ finished, checked,

    get the mask around the `critical_points`

    Parameters:
    -----------
    shape: int, or sequence of int,
        shape of the mask (and the original data)
    critical_points: ndarray,
        indices (of the last dimension) of the points around which to be masked (value 1)
    left_bias: int, non-negative
        bias to the left of the critical points for the mask
    right_bias: int, non-negative
        bias to the right of the critical points for the mask
    return_fmt: str, default "mask",
        format of the return values,
        "mask" for the usual mask,
        can also be "intervals", which consists of a list of intervals

    Returns:
    --------
    mask: ndarray or list,
    """
    if isinstance(shape, int):
        shape = (shape,)
    l_itv = [[max(0,cp-left_bias),min(shape[-1],cp+right_bias)] for cp in critical_points]
    if return_fmt.lower() == "mask":
        mask = np.zeros(shape=shape, dtype=int)
        for itv in l_itv:
            mask[..., itv[0]:itv[1]] = 1
    elif return_fmt.lower() == "intervals":
        mask = l_itv
    return mask


def class_weight_to_sample_weight(y:np.ndarray, class_weight:Union[str,List[float],np.ndarray,dict]="balanced") -> np.ndarray:
    """ finished, checked,

    transform class weight to sample weight

    Parameters:
    -----------
    y: ndarray,
        the label (class) of each sample
    class_weight: str, or list, or ndarray, or dict, default "balanced",
        the weight for each sample class,
        if is "balanced", the class weight will automatically be given by 
        if `y` is of string type, then `class_weight` should be a dict,
        if `y` is of numeric type, and `class_weight` is array_like,
        then the labels (`y`) should be continuous and start from 0
    
    Returns:
    --------
    sample_weight: ndarray,
        the array of sample weight
    """
    if not class_weight:
        sample_weight = np.ones_like(y, dtype=float)
        return sample_weight
    
    try:
        sample_weight = y.copy().astype(int)
    except:
        sample_weight = y.copy()
        assert isinstance(class_weight, dict) or class_weight.lower()=="balanced", \
            "if `y` are of type str, then class_weight should be \042balanced\042 or a dict"
    
    if isinstance(class_weight, str) and class_weight.lower() == "balanced":
        classes = np.unique(y).tolist()
        cw = compute_class_weight("balanced", classes=classes, y=y)
        trans_func = lambda s: cw[classes.index(s)]
    else:
        trans_func = lambda s: class_weight[s]
    sample_weight = np.vectorize(trans_func)(sample_weight)
    sample_weight = sample_weight / np.max(sample_weight)
    return sample_weight


def plot_single_lead(t:np.ndarray, sig:np.ndarray, ax:Optional[Any]=None, ticks_granularity:int=0, **kwargs) -> NoReturn:
    """ finished, NOT checked,

    Parameters:
    -----------
    t: ndarray,
        the array of time of the signal
    sig: ndarray,
        the signal itself
    ax: Artist, optional,
        the `Artist` to plot on
    ticks_granularity: int, default 0,
        the granularity to plot axis ticks, the higher the more,
        0 (no ticks) --> 1 (major ticks) --> 2 (major + minor ticks)
    """
    if "plt" not in dir():
        import matplotlib.pyplot as plt
    palette = {"p_waves": "green", "qrs": "red", "t_waves": "pink",}
    plot_alpha = 0.4
    y_range = np.max(np.abs(sig)) + 100
    if ax is None:
        fig_sz_w = int(round(4.8 * (t[-1]-t[0])))
        fig_sz_h = 6 * y_range / 1500
        fig, ax = plt.subplots(figsize=(fig_sz_w, fig_sz_h))
    label = kwargs.get("label", None)
    if label:
        ax.plot(t, sig, label=kwargs.get("label"))
    else:
        ax.plot(t, sig)
    ax.axhline(y=0, linestyle="-", linewidth="1.0", color="red")
    # NOTE that `Locator` has default `MAXTICKS` equal to 1000
    if ticks_granularity >= 1:
        ax.xaxis.set_major_locator(plt.MultipleLocator(0.2))
        ax.yaxis.set_major_locator(plt.MultipleLocator(500))
        ax.grid(which="major", linestyle="-", linewidth="0.5", color="red")
    if ticks_granularity >= 2:
        ax.xaxis.set_minor_locator(plt.MultipleLocator(0.04))
        ax.yaxis.set_minor_locator(plt.MultipleLocator(100))
        ax.grid(which="minor", linestyle=":", linewidth="0.5", color="black")
    
    waves = kwargs.get("waves", {"p_waves":[], "qrs":[], "t_waves":[]})
    for w, l_itv in waves.items():
        for itv in l_itv:
            ax.axvspan(itv[0], itv[1], color=palette[w], alpha=plot_alpha)
    if label:
        ax.legend(loc="upper left")
    ax.set_xlim(t[0], t[-1])
    ax.set_ylim(-y_range, y_range)
    ax.set_xlabel("Time [s]")
    ax.set_ylabel("Voltage [μV]")


def init_logger(log_dir:str, log_file:Optional[str]=None, log_name:Optional[str]=None, mode:str="a", verbose:int=0) -> logging.Logger:
    """ finished, checked,

    Parameters:
    -----------
    log_dir: str,
        directory of the log file
    log_file: str, optional,
        name of the log file
    log_name: str, optional,
        name of the logger
    mode: str, default "a",
        mode of writing the log file, can be one of "a", "w"
    verbose: int, default 0,
        log verbosity

    Returns:
    --------
    logger: Logger
    """
    if log_file is None:
        log_file = f"log_{get_date_str()}.txt"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    log_file = os.path.join(log_dir, log_file)
    print(f"log file path: {log_file}")

    logger = logging.getLogger(log_name or "ECG")  # "ECG" to prevent from using the root logger

    c_handler = logging.StreamHandler(sys.stdout)
    f_handler = logging.FileHandler(log_file)

    if verbose >= 2:
        print("levels of c_handler and f_handler are set DEBUG")
        c_handler.setLevel(logging.DEBUG)
        f_handler.setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)
    elif verbose >= 1:
        print("level of c_handler is set INFO, level of f_handler is set DEBUG")
        c_handler.setLevel(logging.INFO)
        f_handler.setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)
    else:
        print("levels of c_handler and f_handler are set WARNING")
        c_handler.setLevel(logging.WARNING)
        f_handler.setLevel(logging.WARNING)
        logger.setLevel(logging.WARNING)

    c_format = logging.Formatter("%(name)s - %(levelname)s - %(message)s")
    f_format = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    c_handler.setFormatter(c_format)
    f_handler.setFormatter(f_format)

    logger.addHandler(c_handler)
    logger.addHandler(f_handler)

    return logger


def get_date_str(fmt:Optional[str]=None):
    """ finished, checked,

    Parameters:
    -----------
    fmt: str, optional,
        format of the string of date

    Returns:
    --------
    date_str: str,
        current time in the `str` format
    """
    now = datetime.datetime.now()
    date_str = now.strftime(fmt or "%m-%d_%H-%M")
    return date_str


def rdheader(header_data:Union[str, Sequence[str]]) -> Union[Record, MultiRecord]:
    """ finished, checked,
    
    modified from `wfdb.rdheader`

    Parameters
    ----------
    head_data: str, or sequence of str,
        path of the .hea header file, or lines of the .hea header file
    """
    if isinstance(header_data, str):
        if not header_data.endswith(".hea"):
            _header_data = header_data + ".hea"
        else:
            _header_data = header_data
        if not os.path.isfile(_header_data):
            raise FileNotFoundError
        with open(_header_data, "r") as f:
            _header_data = f.read().splitlines()
    # Read the header file. Separate comment and non-comment lines
    header_lines, comment_lines = [], []
    for line in _header_data:
        striped_line = line.strip()
        # Comment line
        if striped_line.startswith("#"):
            comment_lines.append(striped_line)
        # Non-empty non-comment line = header line.
        elif striped_line:
            # Look for a comment in the line
            ci = striped_line.find("#")
            if ci > 0:
                header_lines.append(striped_line[:ci])
                # comment on same line as header line
                comment_lines.append(striped_line[ci:])
            else:
                header_lines.append(striped_line)

    # Get fields from record line
    record_fields = _header._parse_record_line(header_lines[0])

    # Single segment header - Process signal specification lines
    if record_fields["n_seg"] is None:
        # Create a single-segment WFDB record object
        record = Record()

        # There are signals
        if len(header_lines)>1:
            # Read the fields from the signal lines
            signal_fields = _header._parse_signal_lines(header_lines[1:])
            # Set the object's signal fields
            for field in signal_fields:
                setattr(record, field, signal_fields[field])

        # Set the object's record line fields
        for field in record_fields:
            if field == "n_seg":
                continue
            setattr(record, field, record_fields[field])
    # Multi segment header - Process segment specification lines
    else:
        # Create a multi-segment WFDB record object
        record = MultiRecord()
        # Read the fields from the segment lines
        segment_fields = _header._read_segment_lines(header_lines[1:])
        # Set the object's segment fields
        for field in segment_fields:
            setattr(record, field, segment_fields[field])
        # Set the objects' record fields
        for field in record_fields:
            setattr(record, field, record_fields[field])

        # Determine whether the record is fixed or variable
        if record.seg_len[0] == 0:
            record.layout = "variable"
        else:
            record.layout = "fixed"

    # Set the comments field
    record.comments = [line.strip(" \t#") for line in comment_lines]

    return record


def ensure_lead_fmt(values:Sequence[Real], n_leads:int=12, fmt:str="lead_first") -> np.ndarray:
    """ finished, checked,

    ensure the `n_leads`-lead (ECG) signal to be of the format of `fmt`

    Parameters:
    -----------
    values: sequence,
        values of the `n_leads`-lead (ECG) signal
    n_leads: int, default 12,
        number of leads
    fmt: str, default "lead_first", case insensitive,
        format of the output values, can be one of
        "lead_first" (alias "channel_first"), "lead_last" (alias "channel_last")

    Returns:
    --------
    out_values: ndarray,
        ECG signal in the format of `fmt`
    """
    out_values = np.array(values)
    lead_dim = np.where(np.array(out_values.shape) == n_leads)[0]
    if not any([[0] == lead_dim or [1] == lead_dim]):
        raise ValueError(f"not valid {n_leads}-lead signal")
    lead_dim = lead_dim[0]
    if (lead_dim == 1 and fmt.lower() in ["lead_first", "channel_first"]) \
        or (lead_dim == 0 and fmt.lower() in ["lead_last", "channel_last"]):
        out_values = out_values.T
        return out_values
    return out_values


def ensure_siglen(values:Sequence[Real], siglen:int, fmt:str="lead_first") -> np.ndarray:
    """ finished, checked,

    ensure the (ECG) signal to be of length `siglen`,
    strategy:
        if `values` has length greater than `siglen`,
        the central `siglen` samples will be adopted;
        otherwise, zero padding will be added to both sides

    Parameters:
    -----------
    values: sequence,
        values of the `n_leads`-lead (ECG) signal
    siglen: int,
        length of the signal supposed to have
    fmt: str, default "lead_first", case insensitive,
        format of the input and output values, can be one of
        "lead_first" (alias "channel_first"), "lead_last" (alias "channel_last")

    Returns:
    --------
    out_values: ndarray,
        ECG signal in the format of `fmt` and of fixed length `siglen`
    """
    if fmt.lower() in ["channel_last", "lead_last"]:
        _values = np.array(values).T
    else:
        _values = np.array(values).copy()
    original_siglen = _values.shape[1]
    n_leads = _values.shape[0]

    if original_siglen >= siglen:
        start = (original_siglen - siglen) // 2
        end = start + siglen
        out_values = _values[..., start:end]
    else:
        pad_len = siglen - original_siglen
        pad_left = pad_len // 2
        pad_right = pad_len - pad_left
        out_values = np.concatenate([np.zeros((n_leads, pad_left)), _values, np.zeros((n_leads, pad_right))], axis=1)

    if fmt.lower() in ["channel_last", "lead_last"]:
        out_values = out_values.T
    
    return out_values


ECGWaveForm = namedtuple(
    typename="ECGWaveForm",
    field_names=["name", "onset", "offset", "peak", "duration"],
)


def masks_to_waveforms(masks:np.ndarray,
                       class_map:Dict[str, int],
                       fs:Real,
                       mask_format:str="channel_first",
                       leads:Optional[Sequence[str]]=None) -> Dict[str, List[ECGWaveForm]]:
    """ finished, checked,

    convert masks into lists of waveforms

    Parameters:
    -----------
    masks: ndarray,
        wave delineation in the form of masks,
        of shape (n_leads, seq_len), or (seq_len,)
    class_map: dict,
        class map, mapping names to waves to numbers from 0 to n_classes-1,
        the keys should contain "pwave", "qrs", "twave"
    fs: real number,
        sampling frequency of the signal corresponding to the `masks`,
        used to compute the duration of each waveform
    mask_format: str, default "channel_first",
        format of the mask, used only when `masks.ndim = 2`
        "channel_last" (alias "lead_last"), or
        "channel_first" (alias "lead_first")
    leads: str or list of str, optional,
        the names of leads corresponding to the channels of the `masks`

    Returns:
    --------
    waves: dict,
        each item value is a list containing the `ECGWaveForm`s corr. to the lead;
        each item key is from `leads` if `leads` is set,
        otherwise would be "lead_1", "lead_2", ..., "lead_n"
    """
    if masks.ndim == 1:
        _masks = masks[np.newaxis,...]
    elif masks.ndim == 2:
        if mask_format.lower() not in ["channel_first", "lead_first",]:
            _masks = masks.T
        else:
            _masks = masks.copy()
    else:
        raise ValueError(f"masks should be of dim 1 or 2, but got a {masks.ndim}d array")

    _leads = [f"lead_{idx+1}" for idx in range(_masks.shape[0])] if leads is None else leads
    assert len(_leads) == _masks.shape[0]

    _class_map = ED(deepcopy(class_map))

    waves = ED({lead_name:[] for lead_name in _leads})
    for channel_idx, lead_name in enumerate(_leads):
        current_mask = _masks[channel_idx,...]
        for wave_name, wave_number in _class_map.items():
            if wave_name.lower() not in ["pwave", "qrs", "twave",]:
                continue
            current_wave_inds = np.where(current_mask==wave_number)[0]
            if len(current_wave_inds) == 0:
                continue
            np.where(np.diff(current_wave_inds)>1)
            split_inds = np.where(np.diff(current_wave_inds)>1)[0].tolist()
            split_inds = sorted(split_inds+[i+1 for i in split_inds])
            split_inds = [0] + split_inds + [len(current_wave_inds)-1]
            for i in range(len(split_inds)//2):
                itv_start = current_wave_inds[split_inds[2*i]]
                itv_end = current_wave_inds[split_inds[2*i+1]]+1
                w = ECGWaveForm(
                    name=wave_name.lower(),
                    onset=itv_start,
                    offset=itv_end,
                    peak=np.nan,
                    duration=1000*(itv_end-itv_start)/fs,  # ms
                )
                waves[lead_name].append(w)
        waves[lead_name].sort(key=lambda w: w.onset)
    return waves


def list_sum(l:Sequence[list]) -> list:
    """ finished, checked,

    Parameters:
    -----------
    l: sequence of list,
        the sequence of lists to obtain the summation

    Returns:
    --------
    l_sum: list,
        sum of `l`,
        i.e. if l = [list1, list2, ...], then l_sum = list1 + list2 + ...
    """
    l_sum = reduce(lambda a,b: a+b, l, [])
    return l_sum
