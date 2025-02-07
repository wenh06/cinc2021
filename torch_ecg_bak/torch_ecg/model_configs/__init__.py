"""
"""

from .cnn import (
    # vgg
    vgg_block_basic, vgg_block_mish, vgg_block_swish,
    vgg16, vgg16_leadwise,
    # ResNet
    # vanilla resnet
    resnet_block_basic, resnet_bottle_neck,
    resnet_bottle_neck_B, resnet_bottle_neck_D,
    resnet_block_basic_se, resnet_bottle_neck_se,
    resnet_block_basic_nl, resnet_bottle_neck_nl,
    resnet_block_basic_gc, resnet_bottle_neck_gc,
    # vanilla resnet
    resnet_vanilla_18, resnet_vanilla_34, resnet_vanilla_50,
    resnet_vanilla_101, resnet_vanilla_152,
    resnext_vanilla_50_32x4d, resnext_vanilla_101_32x8d,
    resnet_vanilla_wide_50_2, resnet_vanilla_wide_101_2,
    # cpsc2018 resnet
    resnet_cpsc2018, resnet_cpsc2018_leadwise,
    # smaller resnets
    resnetN, resnetNB, resnetNS, resnetNBS,
    # stanford resnet
    resnet_block_stanford, resnet_stanford,
    # ResNet Nature Communications
    resnet_nature_comm,
    resnet_nature_comm_se, resnet_nature_comm_nl, resnet_nature_comm_gc,
    resnet_nature_comm_bottle_neck, resnet_nature_comm_bottle_neck_se,
    resnet_nature_comm_bottle_neck_gc, resnet_nature_comm_bottle_neck_nl,
    # TResNet
    tresnetF, tresnetP, tresnetN, tresnetS,
    tresnetM, tresnetL, tresnetXL,
    tresnetM_V2,
    # cpsc2018 SOTA
    cpsc_block_basic, cpsc_block_mish, cpsc_block_swish,
    cpsc_2018, cpsc_2018_leadwise,
    # multi_scopic
    multi_scopic_block,
    multi_scopic, multi_scopic_leadwise,
    # vanilla densenet
    densenet_vanilla,
    # custom densenet
    densenet_leadwise,
    # vanilla xception
    xception_vanilla,
    # custom xception
    xception_leadwise,
    # vanilla mobilenets
    mobilenet_v1_vanilla,
)
from .rnn import lstm, attention
from .mlp import linear
from .attn import (
    non_local, squeeze_excitation, global_context,
    transformer,
)

from .ati_cnn import ATI_CNN_CONFIG
from .ecg_crnn import ECG_CRNN_CONFIG
from .ecg_seq_lab_net import ECG_SEQ_LAB_NET_CONFIG
from .ecg_subtract_unet import ECG_SUBTRACT_UNET_CONFIG
from .ecg_unet import ECG_UNET_VANILLA_CONFIG
from .ecg_yolo import ECG_YOLO_CONFIG
from .rr_lstm import RR_AF_CRF_CONFIG, RR_AF_VANILLA_CONFIG, RR_LSTM_CONFIG


__all__ = [
    # building blocks

    # CNN
    # vgg
    "vgg_block_basic", "vgg_block_mish", "vgg_block_swish",
    "vgg16", "vgg16_leadwise",
    # ResNet
    # resnet building blocks
    "resnet_block_basic", "resnet_bottle_neck",
    "resnet_bottle_neck_B", "resnet_bottle_neck_D",
    "resnet_block_basic_se", "resnet_bottle_neck_se",
    "resnet_block_basic_nl", "resnet_bottle_neck_nl",
    "resnet_block_basic_gc", "resnet_bottle_neck_gc",
    # smaller resnets
    "resnetN", "resnetNB", "resnetNS", "resnetNBS",
    # vanilla resnet
    "resnet_vanilla_18", "resnet_vanilla_34",
    "resnet_vanilla_50", "resnet_vanilla_101", "resnet_vanilla_152",
    "resnext_vanilla_50_32x4d", "resnext_vanilla_101_32x8d",
    "resnet_vanilla_wide_50_2", "resnet_vanilla_wide_101_2",
    # cpsc2018 resnet
    "resnet_cpsc2018", "resnet_cpsc2018_leadwise",
    # stanford resnet
    "resnet_block_stanford", "resnet_stanford",
    # ResNet Nature Communications
    "resnet_nature_comm",
    "resnet_nature_comm_se", "resnet_nature_comm_nl", "resnet_nature_comm_gc",
    "resnet_nature_comm_bottle_neck", "resnet_nature_comm_bottle_neck_se",
    "resnet_nature_comm_bottle_neck_gc", "resnet_nature_comm_bottle_neck_nl",
    # TresNet
    "tresnetF", "tresnetP", "tresnetN", "tresnetS",
    "tresnetM", "tresnetL", "tresnetXL",
    "tresnetM_V2",
    # cpsc2018 SOTA
    "cpsc_block_basic", "cpsc_block_mish", "cpsc_block_swish",
    "cpsc_2018", "cpsc_2018_leadwise",
    # multi_scopic
    "multi_scopic_block",
    "multi_scopic", "multi_scopic_leadwise",
    # vanilla densenet
    "densenet_vanilla",
    # custom densenet
    "densenet_leadwise",
    # vanilla xception
    "xception_vanilla",
    # custom xception
    "xception_leadwise",
    # vanilla mobilenets
    "mobilenet_v1_vanilla",

    # RNN
    "lstm",
    "attention",

    # MLP
    "linear",

    # ATTN
    "non_local",
    "squeeze_excitation",
    "global_context",
    "transformer",


    # downstream tasks
    "ATI_CNN_CONFIG",
    "ECG_CRNN_CONFIG",
    "ECG_SEQ_LAB_NET_CONFIG",
    "ECG_SUBTRACT_UNET_CONFIG",
    "ECG_UNET_VANILLA_CONFIG",
    "ECG_YOLO_CONFIG",
    "RR_AF_CRF_CONFIG", "RR_AF_VANILLA_CONFIG", "RR_LSTM_CONFIG",
]
