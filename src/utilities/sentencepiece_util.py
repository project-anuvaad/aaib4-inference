import sentencepiece as spm
import sys, getopt
from anuvaad_auditor.loghandler import log_info, log_exception
from utilities import MODULE_CONTEXT
import os


def encode_as_pieces(load_model,src_file,tgt_file):
    # makes segmenter instance and loads the model file (m.model)
    try:
        sp = spm.SentencePieceProcessor()
        sp.load(load_model)
        with open(src_file) as xh:    
            with open(tgt_file,"w") as outfile:
                xlines= xh.readlines()
        
                for i in range(len(xlines)):
                    encLine = sp.encode_as_pieces(xlines[i])
                    outfile.write(str(encLine))
                    outfile.write("\n")
    except Exception as e:
        print("something went wrong!: ",e)
        print("Unexpected error:", sys.exc_info()[0])
        raise

def encode_line(load_model,line):
    # makes segmenter instance and loads the model file (m.model)
    try:
        sp = spm.SentencePieceProcessor()
        sp.load(load_model)
        log_info("encoding using sp model {}".format(load_model),MODULE_CONTEXT)
        return sp.encode_as_pieces(line)
    except Exception as e:
        log_exception("something went wrong!",MODULE_CONTEXT,e)
        log_exception("Unexpected error: %s"% sys.exc_info()[0],MODULE_CONTEXT,e)
        return ""                 


def decode_line(load_model,line):
    # makes segmenter instance and loads the model file (m.model)
    try:
        sp = spm.SentencePieceProcessor()
        sp.load(load_model)
        if not line.startswith("["):
            line = "["+line
        if not line.endswith("]"):
            line = line+"]"     
        line = line[0]+line[1:-1].replace('[',"")+line[-1] 
        line = line[0]+line[1:-1].replace(']',"")+line[-1]  
        log_info("decoding using sp model {}".format(load_model),MODULE_CONTEXT)
        if "<unk>" in line:
            line = line.replace("<unk>","")
        return sp.DecodePieces(eval(line))
    except Exception as e:
        log_exception("something went wrong! {}".format(e),MODULE_CONTEXT,e)
        log_exception("Unexpected error: %s"% sys.exc_info()[0],MODULE_CONTEXT,e)
        return ""
    
  
if __name__ == '__main__':
    if sys.argv[1] == "train":
        train_spm(sys.argv[2],sys.argv[3],sys.argv[4],sys.argv[5])
    elif sys.argv[1] == "encode":
        encode_as_pieces(sys.argv[2],sys.argv[3],sys.argv[4])
    elif sys.argv[1] == "decode":
        decode_as_pieces(sys.argv[2],sys.argv[3],sys.argv[4])
    else:
        print("invalid request",sys.argv)
           
