#!/bin/bash
set -euxo pipefail

owner='pytest-dev'
repo='pytest'


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


conda create -n pytest_33 python==3.7 -y && \
conda activate pytest_33 && \
pip install hypothesis==4.38.1 jinja2==3.1.6 decorator==5.1.1 twisted==19.10.0 xdist==0.0.2 pexpect==4.9.0 nose==1.3.7 requests==2.31.0 mock==5.2.0 attrs==19.1.0

# python -m pip install -v --no-use-pep517 --no-build-isolation -e .