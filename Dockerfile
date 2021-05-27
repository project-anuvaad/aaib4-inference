FROM python:3.7.9
COPY / /app
WORKDIR /app
RUN pip install --upgrade pip
RUN pip install -r src/requirements.txt
RUN git clone https://github.com/pytorch/fairseq
WORKDIR fairseq
RUN pip install ./
WORKDIR /app/src/tools
RUN git clone https://github.com/anoopkunchukuttan/indic_nlp_library.git 
RUN git clone https://github.com/anoopkunchukuttan/indic_nlp_resources.git 
WORKDIR /app
CMD ["python", "/app/src/app.py"]