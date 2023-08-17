import re

def capture_beginning_punctuations(sentences):
    modified_sentences = []
    start_punc = []
    all_punc_flag = []
    for sent in sentences:
        punctuations = re.match(r'^[\W_\d\s]+', sent)
        if punctuations:
            mod_sent = re.sub(r'^[\W_\d\s]+', '', sent)
            #modified_sentences.append(re.sub(r'^[\W_\d\s]+', '', sent))
            if mod_sent == '':
                modified_sentences.append(sent)
                start_punc.append(punctuations.group())
                all_punc_flag.append(1)
            else:
                start_punc.append(punctuations.group())
                modified_sentences.append(mod_sent)
                all_punc_flag.append(0)
        else:
            modified_sentences.append(sent)
            start_punc.append('')
            all_punc_flag.append(0)
    return modified_sentences, start_punc, all_punc_flag

