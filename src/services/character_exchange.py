def exchng_ya_or(sentences):

    """
    This replace the ଯ଼  character by ୟ 
    """
    modified_sentences = []
    for sent in sentences:
        sent = sent.replace("ଯ଼", "ୟ")
        modified_sentences.append(sent)
    return modified_sentences
