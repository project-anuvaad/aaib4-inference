FROM anuvaadio/aai4b-nmt-inference:74-7375528
# FROM nvidia/cuda:11.0-base
CMD nvidia-smi
RUN apt-get -y update 
# RUN apt-get -y install python3
# RUN apt-get -y install python3-pip
RUN apt-get install -y locales locales-all
ENV LC_ALL en_US.UTF-8
ENV LANG en_US.UTF-8
ENV LANGUAGE en_US.UTF-8
COPY / /app
WORKDIR /app
RUN pip3 install --upgrade pip
RUN pip3 install -r src/requirements.txt
# RUN apt-get -y install git
RUN git clone https://github.com/pytorch/fairseq.git
COPY /app/src/utilities/hub_utils.py /app/fairseq/fairseq
WORKDIR fairseq
RUN pip3 install ./
WORKDIR /app/src/tools
RUN git clone https://github.com/anoopkunchukuttan/indic_nlp_library.git 
RUN git clone https://github.com/anoopkunchukuttan/indic_nlp_resources.git 
WORKDIR /app
COPY start.sh /usr/bin/start.sh
RUN chmod +x /usr/bin/start.sh
CMD ["/usr/bin/start.sh"]
