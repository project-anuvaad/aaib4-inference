from indicnlp.tokenize.sentence_tokenize import sentence_split
import nltk
from nltk.tokenize import sent_tokenize
nltk.download("punkt")


def sentence_tokenize_indic(org_inputs, src_lang):
    """
    This function is used to tokenize a paragraph on the sentence level for indic languages.
    """
    new_inputs = org_inputs.copy()
    inputs = []
    sent_count = []
    for new_sent in new_inputs:
        tokenize_input = sentence_split(new_sent, src_lang)
        sent_count.append(len(tokenize_input))
        for ele_sent in tokenize_input:
            inputs.append(ele_sent) 
    return inputs, sent_count
    
 
def sentence_tokenize_english(org_inputs, src_lang):
    """
    This function is used to tokenize a paragraph on the sentence level for English language.
    """
    new_inputs = org_inputs.copy()
    inputs = []
    sent_count = []
    for new_sent in new_inputs:
        tokenize_input = sent_tokenize(new_sent)
        sent_count.append(len(tokenize_input))
        for ele_sent in tokenize_input:
            inputs.append(ele_sent) 
    return inputs, sent_count
    
    
def sentence_detokenize_paragraph(translation, sent_count):
    """
    This function is used to merge the split (tokenize) sentences within a paragraph.
    """
    translation1 = []
    current_index = 0
    for ele in sent_count:
        next_index = current_index + ele
        translation1.append(" ".join(translation[current_index:next_index]))
        current_index = next_index
    return translation1
