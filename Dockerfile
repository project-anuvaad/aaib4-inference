FROM nvidia/cuda:10.2-base
CMD nvidia-smi
RUN apt-get update
COPY / /app
WORKDIR /app
RUN pip3 install --upgrade pip
RUN pip3 install -r src/requirements.txt
RUN git clone https://github.com/pytorch/fairseq
WORKDIR fairseq
RUN pip3 install ./
WORKDIR /app/src/tools
RUN git clone https://github.com/anoopkunchukuttan/indic_nlp_library.git 
RUN git clone https://github.com/anoopkunchukuttan/indic_nlp_resources.git 
WORKDIR /app
CMD ["python3", "/app/src/app.py"]