#!/bin/bash
set -euxo pipefail

owner='pylint-dev'
repo='pylint'


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
apt-get update && apt-get install -y libenchant-2-dev hunspell-en-us

conda create -n pylint_210 python==3.10 -y && \
conda activate pylint_210 && \
pip install setuptools==58.0.0
# python -m pip install -v --no-use-pep517 --no-build-isolation -e .