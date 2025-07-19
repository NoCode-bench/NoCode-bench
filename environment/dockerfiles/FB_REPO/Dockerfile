# build repo image by fb_base
FROM fb_base:dev
# FROM my_app:test
ARG REPO_NAME


# put env install cmds in sh file
COPY ./setup_$REPO_NAME.sh /root/
RUN sed -i -e 's/\r$//' /root/setup_$REPO_NAME.sh
RUN /bin/bash /root/setup_$REPO_NAME.sh

WORKDIR /root/$REPO_NAME

# docker build -f ./dockerfiles/FB_REPO/Dockerfile --build-arg REPO_NAME=repo_name -t fb_repo_name:dev .
# docker build --network host -f ./dockerfiles/FB_REPO/Dockerfile --build-arg REPO_NAME=seaborn -t fb_seaborn:dev .
# docker run -it --name fb_repo_name fb_base:dev /bin/bash
