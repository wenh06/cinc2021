"""
"""
import traceback


if __name__ == "__main__":
    try:
        try:
            # in cfg_models.py
            from torch_ecg.torch_ecg.model_configs import (  # noqa: F401
                # cnn bankbone
                vgg_block_basic,
                vgg_block_mish,
                vgg_block_swish,
                vgg16,
                vgg16_leadwise,
                resnet_block_basic,
                resnet_bottle_neck_B,
                resnet_bottle_neck_D,
                resnet_block_basic_se,
                resnet_block_basic_gc,
                resnet_bottle_neck_se,
                resnet_bottle_neck_gc,
                resnet_nature_comm,
                resnet_nature_comm_se,
                resnet_nature_comm_gc,
                resnet_nature_comm_bottle_neck,
                resnet_nature_comm_bottle_neck_se,
                resnetN,
                resnetNB,
                resnetNS,
                resnetNBS,
                tresnetF,
                tresnetP,
                tresnetN,
                tresnetS,
                tresnetM,
                multi_scopic_block,
                multi_scopic,
                multi_scopic_leadwise,
                densenet_leadwise,
                xception_leadwise,
                # lstm
                lstm,
                attention,
                # mlp
                linear,
                # attn
                non_local,
                squeeze_excitation,
                global_context,
                # the whole model config
                ECG_CRNN_CONFIG,
            )

            # in model.py
            from torch_ecg.torch_ecg.models.ecg_crnn import ECG_CRNN  # noqa: F401

            # in train.py
            from torch_ecg.torch_ecg.models.loss import (  # noqa: F401
                BCEWithLogitsWithClassWeightLoss,
                AsymmetricLoss,
            )
            from torch_ecg.torch_ecg.utils.utils_nn import (  # noqa: F401
                default_collate_fn as collate_fn,
            )
            from torch_ecg.torch_ecg.utils.misc import (  # noqa: F401
                init_logger,
                get_date_str,
                dict_to_str,
                str2bool,
            )
            from torch_ecg.torch_ecg._preprocessors import PreprocManager  # noqa: F401
            from torch_ecg.torch_ecg.augmenters import AugmenterManager  # noqa: F401
            from torch_ecg.torch_ecg.utils.trainer import BaseTrainer  # noqa: F401
        except Exception:
            print("import torch_ecg directly")
            # in cfg_models.py
            from torch_ecg.model_configs import (  # noqa: F401
                # cnn bankbone
                vgg_block_basic,
                vgg_block_mish,
                vgg_block_swish,
                vgg16,
                vgg16_leadwise,
                resnet_block_basic,
                resnet_bottle_neck_B,
                resnet_bottle_neck_D,
                resnet_block_basic_se,
                resnet_block_basic_gc,
                resnet_bottle_neck_se,
                resnet_bottle_neck_gc,
                resnet_nature_comm,
                resnet_nature_comm_se,
                resnet_nature_comm_gc,
                resnet_nature_comm_bottle_neck,
                resnet_nature_comm_bottle_neck_se,
                resnetN,
                resnetNB,
                resnetNS,
                resnetNBS,
                tresnetF,
                tresnetP,
                tresnetN,
                tresnetS,
                tresnetM,
                multi_scopic_block,
                multi_scopic,
                multi_scopic_leadwise,
                densenet_leadwise,
                xception_leadwise,
                # lstm
                lstm,
                attention,
                # mlp
                linear,
                # attn
                non_local,
                squeeze_excitation,
                global_context,
                # the whole model config
                ECG_CRNN_CONFIG,
            )

            # in model.py
            from torch_ecg.models.ecg_crnn import ECG_CRNN  # noqa: F401

            # in train.py
            from torch_ecg.models.loss import (  # noqa: F401
                BCEWithLogitsWithClassWeightLoss,
                AsymmetricLoss,
            )
            from torch_ecg.utils.utils_nn import (
                default_collate_fn as collate_fn,
            )  # noqa: F401
            from torch_ecg.utils.misc import (  # noqa: F401
                init_logger,
                get_date_str,
                dict_to_str,
                str2bool,
            )
            from torch_ecg._preprocessors import PreprocManager  # noqa: F401
            from torch_ecg.augmenters import AugmenterManager  # noqa: F401
            from torch_ecg.utils.trainer import BaseTrainer  # noqa: F401

        print("successfully import torch_ecg from the submodule!")
    except Exception as e:
        print("failed to import torch_ecg from the submodule!")
        traceback.print_exc()

    try:
        # in cfg.py
        from torch_ecg_bak.torch_ecg.model_configs import (  # noqa: F401, F811
            # cnn bankbone
            vgg_block_basic,
            vgg_block_mish,
            vgg_block_swish,
            vgg16,
            vgg16_leadwise,
            resnet_block_basic,
            resnet_bottle_neck_B,
            resnet_bottle_neck_D,
            resnet_block_basic_se,
            resnet_block_basic_gc,
            resnet_bottle_neck_se,
            resnet_bottle_neck_gc,
            resnet_nature_comm,
            resnet_nature_comm_se,
            resnet_nature_comm_gc,
            resnet_nature_comm_bottle_neck,
            resnet_nature_comm_bottle_neck_se,
            resnetN,
            resnetNB,
            resnetNS,
            resnetNBS,
            tresnetF,
            tresnetP,
            tresnetN,
            tresnetS,
            tresnetM,
            multi_scopic_block,
            multi_scopic,
            multi_scopic_leadwise,
            densenet_leadwise,
            xception_leadwise,
            # lstm
            lstm,
            attention,
            # mlp
            linear,
            # attn
            non_local,
            squeeze_excitation,
            global_context,
            # the whole model config
            ECG_CRNN_CONFIG,
        )

        # in model.py
        from torch_ecg_bak.torch_ecg.models.ecg_crnn import ECG_CRNN  # noqa: F401, F811

        # in train.py
        from torch_ecg_bak.torch_ecg.models.loss import (  # noqa: F401, F811
            BCEWithLogitsWithClassWeightLoss,
            AsymmetricLoss,
        )
        from torch_ecg_bak.torch_ecg.utils.utils_nn import (  # noqa: F401, F811
            default_collate_fn as collate_fn,
        )
        from torch_ecg_bak.torch_ecg.utils.misc import (  # noqa: F401, F811
            init_logger,
            get_date_str,
            dict_to_str,
            str2bool,
        )
        from torch_ecg_bak.torch_ecg._preprocessors import (  # noqa: F401, F811
            PreprocManager,
        )  # noqa: F401, F811
        from torch_ecg_bak.torch_ecg.augmenters import (  # noqa: F401, F811
            AugmenterManager,
        )  # noqa: F401, F811
        from torch_ecg_bak.torch_ecg.utils.trainer import (  # noqa: F401, F811
            BaseTrainer,
        )  # noqa: F401, F811

        print("successfully import torch_ecg from the backup folder!")
    except Exception as e:
        print("failed to import torch_ecg from the backup folder!")
        traceback.print_exc()

    import torch

    cuda_is_available = " " if torch.cuda.is_available() else " not "
    print(f"torch version == {torch.__version__}")
    print(f"cuda is{cuda_is_available}available")
