import re

def capture_beginning_punctuations(sentences):
    modified_sentences = []
    start_punc = []
    for sent in sentences:
        punctuations = re.match(r'^[\W_\d\s]+', sent)
        if punctuations:
            mod_sent = re.sub(r'^[\W_\d\s]+', '', sent)
            #modified_sentences.append(re.sub(r'^[\W_\d\s]+', '', sent))
            if mod_sent == '':
                modified_sentences.append(sent)
                start_punc.append('')
            else:
                start_punc.append(punctuations.group())
                modified_sentences.append(mod_sent)
        else:
            modified_sentences.append(sent)
            start_punc.append('')
    return modified_sentences, start_punc

