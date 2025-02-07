# FROM python:3.8.6-slim
# https://hub.docker.com/r/nvidia/cuda/
# FROM nvidia/cuda:11.1.1-devel
# FROM nvidia/cuda:11.1.1-devel-ubuntu20.04
# FROM pytorch/pytorch:1.8.0-cuda11.1-cudnn8-devel
# FROM pytorch/pytorch:1.6.0-cuda10.1-cudnn7-devel

# not fit for the original challenge
FROM pytorch/pytorch:1.10.0-cuda11.3-cudnn8-runtime

# NOTE: The GPU provided by the Challenge is GPU Tesla T4 with nvidiaDriverVersion: 418.40.04
# by checking https://docs.nvidia.com/cuda/cuda-toolkit-release-notes/index.html
# and https://download.pytorch.org/whl/torch_stable.html
# one should use 1.6.0-cuda10.1


## The MAINTAINER instruction sets the author field of the generated images.
LABEL maintainer="wenh06@gmail.com"

## DO NOT EDIT the 3 lines.
RUN mkdir /physionet
COPY ./ /physionet
WORKDIR /physionet

# submodule
# RUN apt-get update && \
#     apt-get upgrade -y && \
#     apt-get install -y git
# RUN git submodule update --init --remote --recursive --merge --progress
# RUN git submodule update --remote --recursive --merge --progress

## Install your dependencies here using apt install, etc.
# RUN apt update && apt upgrade -y && apt clean
# RUN apt install -y python3.8 python3.8-dev python3.8-distutils python3-pip

# latest version of biosppy uses opencv
# https://stackoverflow.com/questions/55313610/importerror-libgl-so-1-cannot-open-shared-object-file-no-such-file-or-directo
RUN apt update
RUN apt install build-essential -y
RUN apt install ffmpeg libsm6 libxext6 vim -y

# RUN apt update && apt install -y --no-install-recommends \
#         build-essential \
#         curl \
#         software-properties-common \
#         unzip

# RUN apt install python3-pip
RUN ln -s /usr/bin/python3 /usr/bin/python && ln -s /usr/bin/pip3 /usr/bin/pip
# RUN pip install --upgrade pip

# http://mirrors.aliyun.com/pypi/simple/
# http://pypi.douban.com/simple/
# RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
# RUN pip install torch==1.8.0+cu111 -f https://download.pytorch.org/whl/torch_stable.html
RUN pip install torch==1.6.0+cu101 -f https://download.pytorch.org/whl/torch_stable.html
# RUN pip install torch
## Include the following line if you have a requirements.txt file.
RUN pip install -r requirements.txt


RUN python docker_test.py


# temporarily commented, await for the updates of the official phase
RUN python test_team_code.py
# RUN python test_model.py ./saved_models ./docker_test_dir/test_data/twelve_leads ./log/test_12leads
# RUN python test_model.py ./saved_models ./docker_test_dir/test_data/six_leads ./log/test_6leads
# RUN python test_model.py ./saved_models ./docker_test_dir/test_data/four_leads ./log/test_4leads
# RUN python test_model.py ./saved_models ./docker_test_dir/test_data/three_leads ./log/test_3leads
# RUN python test_model.py ./saved_models ./docker_test_dir/test_data/two_leads ./log/test_2leads



# commands to run test with docker container:

# cd ~/Jupyter/temp/cinc2021_docker_test/data/
# cp E075* ../test_data
# cd ~/Jupyter/temp/cinc2021_docker_test/cinc2021/

# sudo docker build -t image .
# sudo docker run -it --shm-size=10240m --gpus all -v ~/Jupyter/temp/cinc2021_docker_test/model:/physionet/model -v ~/Jupyter/temp/cinc2021_docker_test/test_data:/physionet/test_data -v ~/Jupyter/temp/cinc2021_docker_test/test_outputs:/physionet/test_outputs -v ~/Jupyter/temp/cinc2021_docker_test/data:/physionet/training_data image bash
# ( or alternatively
# sudo docker pull wenh06/cinc2021:pytorch1.6.0-cuda10.1-cudnn7-devel
# sudo docker run -it --shm-size=10240m --gpus all -v ~/Jupyter/temp/cinc2021_docker_test/model:/physionet/model -v ~/Jupyter/temp/cinc2021_docker_test/test_data:/physionet/test_data -v ~/Jupyter/temp/cinc2021_docker_test/test_outputs:/physionet/test_outputs -v ~/Jupyter/temp/cinc2021_docker_test/data:/physionet/training_data wenh06/cinc2021:pytorch1.6.0-cuda10.1-cudnn7-devel bash
# )

# python train_model.py training_data model
# python test_model.py model test_data test_outputs
