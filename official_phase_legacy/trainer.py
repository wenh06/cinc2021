"""
(CRNN) models training

Training strategy:
------------------
1. the following pairs of classes will be treated the same:

2. the following classes will be determined by the special detectors:
    PR, LAD, RAD, LQRSV, Brady,
    (potentially) SB, STach

3. models will be trained for each tranche separatly:

4. one model will be trained using the whole dataset (consider excluding tranche C? good news is that tranche C mainly consists of "Brady" and "STach", which can be classified using the special detectors)
        
References: (mainly tips for faster and better training)
-----------
1. https://efficientdl.com/faster-deep-learning-in-pytorch-a-guide/
2. (optim) https://www.fast.ai/2018/07/02/adam-weight-decay/
3. (lr) https://spell.ml/blog/lr-schedulers-and-adaptive-optimizers-YHmwMhAAACYADm6F
4. more....

TODO
----
1. add `train_from_checkpoint`
"""

import os
import sys
import time
import logging
import argparse
import textwrap
from copy import deepcopy
from collections import deque, OrderedDict
from typing import Any, Union, Optional, Tuple, Sequence
from numbers import Real, Number

import numpy as np

np.set_printoptions(precision=5, suppress=True)
# try:
#     from tqdm.auto import tqdm
# except ModuleNotFoundError:
#     from tqdm import tqdm
from tqdm import tqdm
import torch
from torch import nn
from torch import optim
from torch import Tensor
from torch.utils.data import DataLoader
import torch.nn.functional as F
from torch.nn.parallel import DistributedDataParallel as DDP, DataParallel as DP
from tensorboardX import SummaryWriter
from easydict import EasyDict as ED

from torch_ecg.torch_ecg.models.loss import BCEWithLogitsWithClassWeightLoss
from torch_ecg.torch_ecg.utils.utils_nn import default_collate_fn as collate_fn
from torch_ecg.torch_ecg.utils.misc import (
    init_logger,
    get_date_str,
    dict_to_str,
    str2bool,
)

# from torch_ecg_bak.torch_ecg.models.loss import BCEWithLogitsWithClassWeightLoss
# from torch_ecg_bak.torch_ecg.utils.utils_nn import default_collate_fn as collate_fn
# from torch_ecg_bak.torch_ecg.utils.misc import (
#     init_logger, get_date_str, dict_to_str, str2bool,
# )
from model import ECG_CRNN_CINC2021
from utils.scoring_metrics import evaluate_scores
from cfg import BaseCfg, TrainCfg, ModelCfg
from dataset import CINC2021

if BaseCfg.torch_dtype.lower() == "double":
    torch.set_default_tensor_type(torch.DoubleTensor)
    _DTYPE = torch.float64
else:
    _DTYPE = torch.float32


__all__ = [
    "train",
]


def train(
    model: nn.Module,
    model_config: dict,
    device: torch.device,
    config: dict,
    logger: Optional[logging.Logger] = None,
    debug: bool = False,
) -> OrderedDict:
    """finished, checked,

    Parameters
    ----------
    model: Module,
        the model to train
    model_config: dict,
        config of the model, to store into the checkpoints
    device: torch.device,
        device on which the model trains
    config: dict,
        configurations of training, ref. `ModelCfg`, `TrainCfg`, etc.
    logger: Logger, optional,
        logger
    debug: bool, default False,
        if True, the training set itself would be evaluated
        to check if the model really learns from the training set

    Returns
    -------
    best_state_dict: OrderedDict,
        state dict of the best model
    """
    msg = f"training configurations are as follows:\n{dict_to_str(config)}"
    if logger:
        logger.info(msg)
    else:
        print(msg)

    if type(model).__name__ in [
        "DataParallel",
    ]:  # TODO: further consider "DistributedDataParallel"
        _model = model.module
    else:
        _model = model

    train_dataset = CINC2021(config=config, training=True)

    if debug:
        val_train_dataset = CINC2021(config=config, training=True)
        val_train_dataset.disable_data_augmentation()
    val_dataset = CINC2021(config=config, training=False)

    n_train = len(train_dataset)
    n_val = len(val_dataset)

    n_epochs = config.n_epochs
    batch_size = config.batch_size
    lr = config.learning_rate

    # https://discuss.pytorch.org/t/guidelines-for-assigning-num-workers-to-dataloader/813/4
    num_workers = 4

    train_loader = DataLoader(
        dataset=train_dataset,
        batch_size=batch_size,
        shuffle=True,
        num_workers=num_workers,
        pin_memory=True,
        drop_last=False,
        collate_fn=collate_fn,
    )

    if debug:
        val_train_loader = DataLoader(
            dataset=val_train_dataset,
            batch_size=batch_size,
            shuffle=True,
            num_workers=num_workers,
            pin_memory=True,
            drop_last=False,
            collate_fn=collate_fn,
        )
    val_loader = DataLoader(
        dataset=val_dataset,
        batch_size=batch_size,
        shuffle=True,
        num_workers=num_workers,
        pin_memory=True,
        drop_last=False,
        collate_fn=collate_fn,
    )

    writer = SummaryWriter(
        log_dir=config.log_dir,
        filename_suffix=f"OPT_{_model.__name__}_{config.cnn_name}_{config.train_optimizer}_LR_{lr}_BS_{batch_size}_tranche_{config.tranches_for_training or 'all'}",
        comment=f"OPT_{_model.__name__}_{config.cnn_name}_{config.train_optimizer}_LR_{lr}_BS_{batch_size}_tranche_{config.tranches_for_training or 'all'}",
    )

    # max_itr = n_epochs * n_train

    msg = textwrap.dedent(
        f"""
        Starting training:
        ------------------
        Epochs:          {n_epochs}
        Batch size:      {batch_size}
        Learning rate:   {lr}
        Training size:   {n_train}
        Validation size: {n_val}
        Device:          {device.type}
        Optimizer:       {config.train_optimizer}
        Dataset classes: {train_dataset.all_classes}
        Class weights:   {train_dataset.class_weights}
        -----------------------------------------
        """
    )
    # print(msg)  # in case no logger
    if logger:
        logger.info(msg)
    else:
        print(msg)

    # learning rate setup
    def burnin_schedule(i):
        """ """
        if i < config.burn_in:
            factor = pow(i / config.burn_in, 4)
        elif i < config.steps[0]:
            factor = 1.0
        elif i < config.steps[1]:
            factor = 0.1
        else:
            factor = 0.01
        return factor

    if config.train_optimizer.lower() == "adam":
        optimizer = optim.Adam(
            params=model.parameters(),
            lr=lr,
            betas=config.betas,
            eps=1e-08,  # default
        )
    elif config.train_optimizer.lower() in ["adamw", "adamw_amsgrad"]:
        optimizer = optim.AdamW(
            params=model.parameters(),
            lr=lr,
            betas=config.betas,
            weight_decay=config.decay,
            eps=1e-08,  # default
            amsgrad=config.train_optimizer.lower().endswith("amsgrad"),
        )
    elif config.train_optimizer.lower() == "sgd":
        optimizer = optim.SGD(
            params=model.parameters(),
            lr=lr,
            momentum=config.momentum,
            weight_decay=config.decay,
        )
    else:
        raise NotImplementedError(
            f"optimizer `{config.train_optimizer}` not implemented!"
        )
    # scheduler = optim.lr_scheduler.LambdaLR(optimizer, burnin_schedule)

    if config.lr_scheduler is None:
        scheduler = None
    elif config.lr_scheduler.lower() == "plateau":
        scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, "max", patience=2)
    elif config.lr_scheduler.lower() == "step":
        scheduler = optim.lr_scheduler.StepLR(
            optimizer, config.lr_step_size, config.lr_gamma
        )
    elif config.lr_scheduler.lower() in [
        "one_cycle",
        "onecycle",
    ]:
        scheduler = optim.lr_scheduler.OneCycleLR(
            optimizer=optimizer,
            max_lr=config.max_lr,
            epochs=n_epochs,
            steps_per_epoch=len(train_loader),
        )
    else:
        raise NotImplementedError(
            f"lr scheduler `{config.lr_scheduler.lower()}` not implemented for training"
        )

    if config.loss == "BCEWithLogitsLoss":
        criterion = nn.BCEWithLogitsLoss()
    elif config.loss == "BCEWithLogitsWithClassWeightLoss":
        criterion = BCEWithLogitsWithClassWeightLoss(
            class_weight=train_dataset.class_weights.to(device=device, dtype=_DTYPE)
        )
    else:
        raise NotImplementedError(f"loss `{config.loss}` not implemented!")
    # scheduler = ReduceLROnPlateau(optimizer, mode="max", verbose=True, patience=6, min_lr=1e-7)
    # scheduler = CosineAnnealingWarmRestarts(optimizer, 0.001, 1e-6, 20)

    save_prefix = f"{_model.__name__}_{config.cnn_name}_{config.rnn_name}_tranche_{config.tranches_for_training or 'all'}_epoch"

    os.makedirs(config.checkpoints, exist_ok=True)
    os.makedirs(config.model_dir, exist_ok=True)

    # monitor for training: challenge metric
    best_state_dict = OrderedDict()
    best_challenge_metric = -np.inf
    best_eval_res = tuple()
    best_epoch = -1
    pseudo_best_epoch = -1

    saved_models = deque()
    model.train()
    global_step = 0
    for epoch in range(n_epochs):
        # train one epoch
        model.train()
        epoch_loss = 0

        with tqdm(
            total=n_train, desc=f"Epoch {epoch + 1}/{n_epochs}", ncols=100
        ) as pbar:
            for epoch_step, (signals, labels) in enumerate(train_loader):
                global_step += 1
                signals = signals.to(device=device, dtype=_DTYPE)
                labels = labels.to(device=device, dtype=_DTYPE)

                preds = model(signals)
                loss = criterion(preds, labels)
                if config.flooding_level > 0:
                    flood = (loss - config.flooding_level).abs() + config.flooding_level
                    epoch_loss += loss.item()
                    optimizer.zero_grad()
                    flood.backward()
                else:
                    epoch_loss += loss.item()
                    optimizer.zero_grad()
                    loss.backward()
                optimizer.step()

                if global_step % config.log_step == 0:
                    writer.add_scalar("train/loss", loss.item(), global_step)
                    if scheduler:
                        writer.add_scalar("lr", scheduler.get_lr()[0], global_step)
                        pbar.set_postfix(
                            **{
                                "loss (batch)": loss.item(),
                                "lr": scheduler.get_lr()[0],
                            }
                        )
                        msg = f"Train step_{global_step}: loss : {loss.item()}, lr : {scheduler.get_lr()[0] * batch_size}"
                    else:
                        pbar.set_postfix(
                            **{
                                "loss (batch)": loss.item(),
                            }
                        )
                        msg = f"Train step_{global_step}: loss : {loss.item()}"
                    # print(msg)  # in case no logger
                    if config.flooding_level > 0:
                        writer.add_scalar("train/flood", flood.item(), global_step)
                        msg = f"{msg}\nflood : {flood.item()}"
                    if logger:
                        logger.info(msg)
                    else:
                        print(msg)
                pbar.update(signals.shape[0])

            writer.add_scalar("train/epoch_loss", epoch_loss, global_step)

            # eval for each epoch using `evaluate`
            if debug:
                eval_train_res = evaluate(
                    model, val_train_loader, config, device, debug, logger=logger
                )
                writer.add_scalar("train/auroc", eval_train_res[0], global_step)
                writer.add_scalar("train/auprc", eval_train_res[1], global_step)
                writer.add_scalar("train/accuracy", eval_train_res[2], global_step)
                writer.add_scalar("train/f_measure", eval_train_res[3], global_step)
                writer.add_scalar(
                    "train/f_beta_measure", eval_train_res[4], global_step
                )
                writer.add_scalar(
                    "train/g_beta_measure", eval_train_res[5], global_step
                )
                writer.add_scalar(
                    "train/challenge_metric", eval_train_res[6], global_step
                )

            eval_res = evaluate(model, val_loader, config, device, debug, logger=logger)
            model.train()
            writer.add_scalar("test/auroc", eval_res[0], global_step)
            writer.add_scalar("test/auprc", eval_res[1], global_step)
            writer.add_scalar("test/accuracy", eval_res[2], global_step)
            writer.add_scalar("test/f_measure", eval_res[3], global_step)
            writer.add_scalar("test/f_beta_measure", eval_res[4], global_step)
            writer.add_scalar("test/g_beta_measure", eval_res[5], global_step)
            writer.add_scalar("test/challenge_metric", eval_res[6], global_step)

            if config.lr_scheduler is None:
                pass
            elif config.lr_scheduler.lower() == "plateau":
                scheduler.step(metrics=eval_res[6])
            elif config.lr_scheduler.lower() == "step":
                scheduler.step()
            elif config.lr_scheduler.lower() in [
                "one_cycle",
                "onecycle",
            ]:
                scheduler.step()

            if debug:
                eval_train_msg = f"""
                train/auroc:             {eval_train_res[0]}
                train/auprc:             {eval_train_res[1]}
                train/accuracy:          {eval_train_res[2]}
                train/f_measure:         {eval_train_res[3]}
                train/f_beta_measure:    {eval_train_res[4]}
                train/g_beta_measure:    {eval_train_res[5]}
                train/challenge_metric:  {eval_train_res[6]}
                """
            else:
                eval_train_msg = ""
            msg = textwrap.dedent(
                f"""
                Train epoch_{epoch + 1}:
                --------------------
                train/epoch_loss:        {epoch_loss}{eval_train_msg}
                test/auroc:              {eval_res[0]}
                test/auprc:              {eval_res[1]}
                test/accuracy:           {eval_res[2]}
                test/f_measure:          {eval_res[3]}
                test/f_beta_measure:     {eval_res[4]}
                test/g_beta_measure:     {eval_res[5]}
                test/challenge_metric:   {eval_res[6]}
                ---------------------------------
                """
            )
            # print(msg)  # in case no logger
            if logger:
                logger.info(msg)
            else:
                print(msg)

            if eval_res[6] > best_challenge_metric:
                best_challenge_metric = eval_res[6]
                best_state_dict = _model.state_dict()
                best_eval_res = deepcopy(eval_res)
                best_epoch = epoch + 1
                pseudo_best_epoch = epoch + 1
            elif config.early_stopping:
                if (
                    eval_res[6]
                    >= best_challenge_metric - config.early_stopping.min_delta
                ):
                    pseudo_best_epoch = epoch + 1
                elif epoch - pseudo_best_epoch >= config.early_stopping.patience:
                    msg = f"early stopping is triggered at epoch {epoch + 1}"
                    if logger:
                        logger.info(msg)
                    else:
                        print(msg)
                    break

            msg = textwrap.dedent(
                f"""
                best challenge metric = {best_challenge_metric},
                obtained at epoch {best_epoch}
            """
            )
            if logger:
                logger.info(msg)
            else:
                print(msg)

            try:
                os.makedirs(config.checkpoints, exist_ok=True)
                # if logger:
                #     logger.info("Created checkpoint directory")
            except OSError:
                pass
            save_suffix = f"epochloss_{epoch_loss:.5f}_fb_{eval_res[4]:.2f}_gb_{eval_res[5]:.2f}_cm_{eval_res[6]:.2f}"
            save_filename = (
                f"{save_prefix}{epoch + 1}_{get_date_str()}_{save_suffix}.pth.tar"
            )
            save_path = os.path.join(config.checkpoints, save_filename)
            torch.save(
                {
                    "model_state_dict": _model.state_dict(),
                    "optimizer_state_dict": optimizer.state_dict(),
                    "model_config": model_config,
                    "train_config": config,
                    "epoch": epoch + 1,
                },
                save_path,
            )
            if logger:
                logger.info(f"Checkpoint {epoch + 1} saved!")
            saved_models.append(save_path)
            # remove outdated models
            if len(saved_models) > config.keep_checkpoint_max > 0:
                model_to_remove = saved_models.popleft()
                try:
                    os.remove(model_to_remove)
                except:
                    logger.info(f"failed to remove {model_to_remove}")

    # save the best model
    if best_challenge_metric > -np.inf:
        if config.final_model_name:
            save_filename = config.final_model_name
        else:
            save_suffix = f"BestModel_fb_{best_eval_res[4]:.2f}_gb_{best_eval_res[5]:.2f}_cm_{best_eval_res[6]:.2f}"
            save_filename = f"{save_prefix}_{get_date_str()}_{save_suffix}.pth.tar"
        save_path = os.path.join(config.model_dir, save_filename)
        torch.save(
            {
                "model_state_dict": best_state_dict,
                "model_config": model_config,
                "train_config": config,
                "epoch": best_epoch,
            },
            save_path,
        )
        if logger:
            logger.info(f"Best model saved to {save_path}!")

    writer.close()

    if logger:
        for h in logger.handlers:
            h.close()
            logger.removeHandler(h)
        del logger
    logging.shutdown()

    return best_state_dict


# def train_one_epoch(model:nn.Module, criterion:nn.Module, optimizer:optim.Optimizer, data_loader:DataLoader, device:torch.device, epoch:int) -> None:
#     """
#     """


@torch.no_grad()
def evaluate(
    model: nn.Module,
    data_loader: DataLoader,
    config: dict,
    device: torch.device,
    debug: bool = True,
    logger: Optional[logging.Logger] = None,
) -> Tuple[float, ...]:
    """finished, checked,

    Parameters
    ----------
    model: Module,
        the model to evaluate
    data_loader: DataLoader,
        the data loader for loading data for evaluation
    config: dict,
        evaluation configurations
    device: torch.device,
        device for evaluation
    debug: bool, default True,
        more detailed evaluation output
    logger: Logger, optional,
        logger to record detailed evaluation output,
        if is None, detailed evaluation output will be printed

    Returns
    -------
    eval_res: tuple of float,
        evaluation results, including
        auroc, auprc, accuracy, f_measure, f_beta_measure, g_beta_measure, challenge_metric
    """
    model.eval()
    prev_aug_status = data_loader.dataset.use_augmentation
    data_loader.dataset.disable_data_augmentation()

    if type(model).__name__ in [
        "DataParallel",
    ]:  # TODO: further consider "DistributedDataParallel"
        _model = model.module
    else:
        _model = model

    all_scalar_preds = []
    all_bin_preds = []
    all_labels = []

    for signals, labels in data_loader:
        signals = signals.to(device=device, dtype=_DTYPE)
        labels = labels.numpy()
        all_labels.append(labels)

        if torch.cuda.is_available():
            torch.cuda.synchronize()
        preds, bin_preds = _model.inference(signals)
        all_scalar_preds.append(preds)
        all_bin_preds.append(bin_preds)

    all_scalar_preds = np.concatenate(all_scalar_preds, axis=0)
    all_bin_preds = np.concatenate(all_bin_preds, axis=0)
    all_labels = np.concatenate(all_labels, axis=0)
    classes = data_loader.dataset.all_classes

    if debug:
        msg = f"all_scalar_preds.shape = {all_scalar_preds.shape}, all_labels.shape = {all_labels.shape}"
        if logger:
            logger.debug(msg)
        else:
            print(msg)
        head_num = 5
        head_scalar_preds = all_scalar_preds[:head_num, ...]
        head_bin_preds = all_bin_preds[:head_num, ...]
        head_preds_classes = [
            np.array(classes)[np.where(row)] for row in head_bin_preds
        ]
        head_labels = all_labels[:head_num, ...]
        head_labels_classes = [np.array(classes)[np.where(row)] for row in head_labels]
        for n in range(head_num):
            msg = textwrap.dedent(
                f"""
            ----------------------------------------------
            scalar prediction:    {[round(n, 3) for n in head_scalar_preds[n].tolist()]}
            binary prediction:    {head_bin_preds[n].tolist()}
            labels:               {head_labels[n].astype(int).tolist()}
            predicted classes:    {head_preds_classes[n].tolist()}
            label classes:        {head_labels_classes[n].tolist()}
            ----------------------------------------------
            """
            )
            if logger:
                logger.debug(msg)
            else:
                print(msg)

    (
        auroc,
        auprc,
        accuracy,
        f_measure,
        f_beta_measure,
        g_beta_measure,
        challenge_metric,
    ) = evaluate_scores(
        classes=classes,
        truth=all_labels,
        scalar_pred=all_scalar_preds,
        binary_pred=all_bin_preds,
    )
    eval_res = (
        auroc,
        auprc,
        accuracy,
        f_measure,
        f_beta_measure,
        g_beta_measure,
        challenge_metric,
    )

    model.train()

    if prev_aug_status:
        data_loader.dataset.enable_data_augmentation()

    return eval_res


def get_args(**kwargs: Any):
    """ """
    cfg = deepcopy(kwargs)
    parser = argparse.ArgumentParser(
        description="Train the Model on CINC2021",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "-l", "--leads", type=int, default=12, help="number of leads", dest="n_leads"
    )
    parser.add_argument(
        "-t",
        "--tranches",
        type=str,
        default="",
        help="the tranches for training",
        dest="tranches_for_training",
    )
    parser.add_argument(
        "-b",
        "--batch-size",
        type=int,
        default=128,
        help="the batch size for training",
        dest="batch_size",
    )
    parser.add_argument(
        "-c",
        "--cnn-name",
        type=str,
        default="multi_scopic_leadwise",
        help="choice of cnn feature extractor",
        dest="cnn_name",
    )
    parser.add_argument(
        "-r",
        "--rnn-name",
        type=str,
        default="none",
        help="choice of rnn structures",
        dest="rnn_name",
    )
    parser.add_argument(
        "-a",
        "--attn-name",
        type=str,
        default="se",
        help="choice of attention structures",
        dest="attn_name",
    )
    parser.add_argument(
        "--keep-checkpoint-max",
        type=int,
        default=20,
        help="maximum number of checkpoints to keep. If set 0, all checkpoints will be kept",
        dest="keep_checkpoint_max",
    )
    # parser.add_argument(
    #     "--optimizer", type=str, default="adam",
    #     help="training optimizer",
    #     dest="train_optimizer")
    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="train with more debugging information",
        dest="debug",
    )

    args = vars(parser.parse_args())

    cfg.update(args)

    return ED(cfg)


if __name__ == "__main__":
    config = get_args(**TrainCfg)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger = init_logger(log_dir=config.log_dir, verbose=2)
    logger.info(f"\n{'*'*20}   Start Training   {'*'*20}\n")
    logger.info(f"Using device {device}")
    logger.info(f"Using torch of version {torch.__version__}")
    logger.info(f"with configuration\n{dict_to_str(config)}")

    tranches = config.tranches_for_training
    if tranches:
        classes = config.tranche_classes[tranches]
    else:
        classes = config.classes

    if config.n_leads == 12:
        model_config = deepcopy(ModelCfg.twelve_leads)
    elif config.n_leads == 6:
        model_config = deepcopy(ModelCfg.six_leads)
    elif config.n_leads == 4:
        model_config = deepcopy(ModelCfg.four_leads)
    elif config.n_leads == 3:
        model_config = deepcopy(ModelCfg.three_leads)
    elif config.n_leads == 2:
        model_config = deepcopy(ModelCfg.two_leads)
    model_config.cnn.name = config.cnn_name
    model_config.rnn.name = config.rnn_name
    model_config.attn.name = config.attn_name

    model = ECG_CRNN_CINC2021(
        classes=classes,
        n_leads=config.n_leads,
        config=model_config,
    )
    model.__DEBUG__ = False

    if torch.cuda.device_count() > 1:
        model = DP(model)
        # model = DDP(model)
    model.to(device=device)

    try:
        train(
            model=model,
            model_config=model_config,
            config=config,
            device=device,
            logger=logger,
            debug=config.debug,
        )
    except KeyboardInterrupt:
        torch.save(
            {
                "model_state_dict": model.state_dict(),
                "model_config": model_config,
                "train_config": config,
            },
            os.path.join(config.checkpoints, "INTERRUPTED.pth.tar"),
        )
        logger.info("Saved interrupt")
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
