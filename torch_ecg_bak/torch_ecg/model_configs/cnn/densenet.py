"""
"""

from itertools import repeat
from copy import deepcopy

import numpy as np
from easydict import EasyDict as ED


__all__ = [
    # vanilla densenet
    "densenet_vanilla",
    # custom densenet
    "densenet_leadwise",
]


densenet_vanilla = ED()
densenet_vanilla.fs = 500
densenet_vanilla.num_layers = [6, 6, 6, 6]
densenet_vanilla.init_num_filters = 64
densenet_vanilla.init_filter_length = 25
densenet_vanilla.init_pool_stride = 2
densenet_vanilla.init_pool_size = 3
densenet_vanilla.init_subsample_mode = "avg"
densenet_vanilla.growth_rates = 16
densenet_vanilla.filter_lengths = 15
densenet_vanilla.subsample_lengths = 2
densenet_vanilla.bn_size = 4
densenet_vanilla.dropout = 0
densenet_vanilla.compression = 0.5
densenet_vanilla.groups = 1
densenet_vanilla.block = ED(building_block="basic")
densenet_vanilla.transition = ED()

densenet_leadwise = deepcopy(densenet_vanilla)
densenet_leadwise.init_num_filters = 12 * 8
densenet_leadwise.groups = 12
