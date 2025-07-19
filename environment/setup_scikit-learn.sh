#!/bin/bash
set -euxo pipefail

owner='scikit-learn'
repo='scikit-learn'

#git config --global http.proxy http://127.0.0.1:7893
#git config --global https.proxy http://127.0.0.1:7893

rm -rf /root/$repo
# pull the repo
git clone https://github.com/$owner/$repo.git /root/$repo
git config --global --add safe.directory "*"

# if you are in china, please set proxy
# set conda proxy
#conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main
#conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/free
#conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/r
#conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/pro
#conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/msys2
#conda config --set show_channel_urls yes
## set pip proxy
#pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

source /opt/miniconda3/etc/profile.d/conda.sh

conda create -n skl_020 python==3.6 -y && \
conda activate skl_020 && \
pip install numpy==1.19.2 scipy==1.5.2 pandas matplotlib cython==0.28.5 attrs==19.1.0 pytest==6.0.0 setuptools --trusted-host pypi.tuna.tsinghua.edu.cn

conda create -n skl_100 python==3.8 -y && \
conda activate skl_100 && \
pip install numpy==1.19.2 scipy==1.5.2 'pandas<2.0.0' 'matplotlib<3.9.0' cython==0.29.24 pytest 'setuptools<60.0'

conda create -n skl_104 python==3.9 -y && \
conda activate skl_104 && \
pip install numpy==1.19.5 scipy==1.6.0 'pandas<2.0.0' 'matplotlib<3.9.0' cython==3.0.10 pytest setuptools
