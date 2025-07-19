#!/bin/bash
set -euxo pipefail

owner='matplotlib'
repo='matplotlib'

apt-get -y update && apt-get -y upgrade && DEBIAN_FRONTEND=noninteractive apt-get install -y imagemagick ffmpeg libfreetype6-dev pkg-config texlive texlive-latex-extra texlive-fonts-recommended texlive-xetex texlive-luatex cm-super inkscape && \
QHULL_URL="http://www.qhull.org/download/qhull-2020-src-8.0.2.tgz" && \
QHULL_TAR="/tmp/qhull-2020-src-8.0.2.tgz" && \
QHULL_BUILD_DIR="/testbed/build" && \
wget -O "$QHULL_TAR" "$QHULL_URL" && \
mkdir -p "$QHULL_BUILD_DIR" && \
tar -xvzf "$QHULL_TAR" -C "$QHULL_BUILD_DIR"


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

conda create -n matplotlib_11 python=3.5 -y && \
conda activate matplotlib_11 && \
pip install --upgrade certifi --trusted-host pypi.tuna.tsinghua.edu.cn && \
pip install pytest 

conda create -n matplotlib_35 python=3.11 -y && \
conda activate matplotlib_35 && \
pip install contourpy==1.1.0 cycler==0.11.0 fonttools==4.42.1 ghostscript kiwisolver==1.4.5 numpy==1.25.2 packaging==23.1 pillow==10.0.0 pikepdf pyparsing==3.0.9 python-dateutil==2.8.2 six==1.16.0 setuptools==68.1.2 setuptools-scm==7.1.0 typing-extensions==4.7.1 pytest pandas

conda create -n matplotlib_31 python=3.8 -y && \
conda activate matplotlib_31 && \
pip install pytest pandas
