#!/bin/bash
set -euxo pipefail

# In "4.1", "4.2", "4.3", "5.0", "5.1", "5.2", "v5.3", run below cmd before pip install -e .
# pre_install: sed -i 's/requires = \["setuptools",/requires = \["setuptools==68.0.0",/' pyproject.toml
# install: python -m pip install -e .[test] --verbose
# test: pytest --color=no -rA
owner='mwaskom'
repo='seaborn'

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

# TODO
conda create -n seaborn_010 python==3.8 -y && \
conda activate seaborn_010 && \
pip install contourpy==1.1.1 cycler==0.12.1 fonttools==4.56.0 importlib-resources==6.4.5 kiwisolver==1.4.7 matplotlib==3.7.5 numpy==1.24.3 packaging==24.2 pandas==2.0.3 pillow==10.4.0 pyparsing==3.1.4 pytest python-dateutil==2.8.2 pytz==2025.1 scipy==1.10.1 six==1.17.0 tzdata==2025.1 zipp==3.20.2
