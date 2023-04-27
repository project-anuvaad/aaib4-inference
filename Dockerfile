#FROM anuvaadio/aai4b-nmt-inference:74-7375528
#FROM nvidia/cuda:11.2.0-base-ubuntu20.04
FROM python:3.8-slim
#### Commented lines below are added to the base image ###
#FROM anuvaadio/ai4b-nmt-inference-base-image:2
#CMD nvidia-smi

#RUN rm -rf /var/lib/apt/lists/*
#ENV DEBIAN_FRONTEND noninteractive
#RUN apt update --fix-missing && apt install -y software-properties-common git locales locales-all --fix-missing
#ENV LC_ALL en_US.UTF-8
#ENV LANG en_US.UTF-8
#ENV LANGUAGE en_US.UTF-8

RUN apt-get update && apt-get -y install python3.8 python3.8-dev python3.8-venv python3.8-distutils python3-pip 
RUN python3 --version && pip3 --version
RUN pip3 install --upgrade pip

WORKDIR /app
RUN git clone https://github.com/pytorch/fairseq.git
WORKDIR fairseq
#RUN git reset --hard b5e7b250913120409b872a940fbafec4d43c7b13
RUN pip3 install ./

WORKDIR /app/src/tools
RUN git clone https://github.com/anoopkunchukuttan/indic_nlp_library.git 
RUN git clone https://github.com/anoopkunchukuttan/indic_nlp_resources.git 

WORKDIR /app
COPY src/requirements.txt ./src/requirements.txt
RUN pip3 install --default-timeout=100 -r src/requirements.txt

COPY download_deps.py ./download_deps.py
RUN python3 download_deps.py

COPY start.sh /usr/bin/start.sh
RUN chmod +x /usr/bin/start.sh
COPY . ./

EXPOSE 5001
CMD ["/usr/bin/start.sh"]
