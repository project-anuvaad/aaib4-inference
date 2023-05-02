from typing import List, Union

import os
from os import truncate
from sacremoses import MosesPunctNormalizer
from sacremoses import MosesTokenizer
from sacremoses import MosesDetokenizer
import codecs
from tqdm import tqdm
from indicnlp.tokenize import indic_tokenize
from indicnlp.tokenize import indic_detokenize
from indicnlp.normalize import indic_normalize
from indicnlp.transliterate import unicode_transliterate

import re
import sentencepiece as spm
import tempfile

from .normalize_regex_inference import normalize, EMAIL_PATTERN
from .language_codes import flores_codes, iso_to_flores

CURRENT_DIRECTORY = os.path.dirname(__file__)

en_tok = MosesTokenizer(lang="en")
en_normalizer = MosesPunctNormalizer()
en_detok = MosesDetokenizer(lang="en")
xliterator = unicode_transliterate.UnicodeIndicTransliterator()
normfactory = indic_normalize.IndicNormalizerFactory()

def apply_vocab_processing(sents: List[str], vocab_processor: spm.SentencePieceProcessor) -> List[str]:
    """
    Applies sentence piece encoding to the batch of input sentences.
    
    Args:
        sents (List[str]): batch of the input sentences.
        vocab_processor (spm.SentencePieceProcessor): SP Tokenizer
    
    Returns:
        List[str]: batch of encoded sentences with sentence piece model
    """
    return [" ".join(vocab_processor.encode(sent, out_type=str)) for sent in sents]

def add_token(sent: str, src_lang: str, tgt_lang: str, delimiter: str = " ") -> str:
    """
    Add special tokens indicating source and target language to the start of the input sentence.
    The resulting string will have the format: "`{src_lang} {tgt_lang} {input_sentence}`".

    Args:
        sent (str): input sentence to be translated.
        src_lang (str): language of the input sentence.
        tgt_lang (str): language in which the input sentence will be translated.
        delimiter (str): separator to add between language tags and input sentence (default: " ").

    Returns:
        str: input sentence with the special tokens added to the start.
    """
    return src_lang + delimiter + tgt_lang + delimiter + sent


def apply_lang_tags(sents: List[str], src_lang: str, tgt_lang: str) -> List[str]:
    """
    Add special tokens indicating source and target language to the start of the each input sentence.
    Each resulting input sentence will have the format: "`{src_lang} {tgt_lang} {input_sentence}`".
    
    Args:
        sent (str): input sentence to be translated.
        src_lang (str): language of the input sentence.
        tgt_lang (str): language in which the input sentence will be translated.

    Returns:
        List[str]: list of input sentences with the special tokens added to the start.
    """
    src_lang, tgt_lang = lang = iso_to_flores[src_lang], iso_to_flores[tgt_lang]
    tagged_sents = []
    for sent in sents:
        tagged_sent = add_token(sent.strip(), src_lang, tgt_lang)
        tagged_sents.append(tagged_sent)
    return tagged_sents


def preprocess_sent(
    sent: str, 
    normalizer: Union[MosesPunctNormalizer, indic_normalize.IndicNormalizerFactory], 
    lang: str
) -> str:
    """
    Preprocess an input text sentence by normalizing, tokenization, and possibly transliterating it.

    Args:
        sent (str): input text sentence to preprocess.
        normalizer (Union[MosesPunctNormalizer, indic_normalize.IndicNormalizerFactory]): an object that performs normalization on the text.
        lang (str): flores language code of the input text sentence.
        
    Returns:
        str: preprocessed input text sentence.
    """
    sent = normalize(sent)
    
    iso_lang = flores_codes[lang]
    
    transliterate = True
    if lang.split("_")[1] in ["Arab", "Olck", "Mtei", "Latn"]:
        transliterate = False
    
    pattern = r'<dnt>(.*?)</dnt>'
    raw_matches = re.findall(pattern, sent)
    
    if iso_lang == "en":
        processed_sent = " ".join(
            en_tok.tokenize(
                en_normalizer.normalize(sent.strip()), escape=False
            )
        )
    elif transliterate:
        # transliterates from the any specific language to devanagari
        # which is why we specify lang2_code as "hi".
        processed_sent = unicode_transliterate.UnicodeIndicTransliterator.transliterate(
            " ".join(indic_tokenize.trivial_tokenize(normalizer.normalize(sent.strip()), iso_lang)),
            iso_lang,
            "hi",
        ).replace(" ् ", "्")
    else:
        # we only need to transliterate for joint training
        processed_sent = " ".join(
            indic_tokenize.trivial_tokenize(normalizer.normalize(sent.strip()), iso_lang)
        )

    processed_sent = processed_sent.replace("< dnt >", "<dnt>")
    processed_sent = processed_sent.replace("< / dnt >", "</dnt>")
    
    processed_sent_matches = re.findall(pattern, processed_sent)
    for raw_match, processed_sent_match in zip(raw_matches, processed_sent_matches):
        processed_sent = processed_sent.replace(processed_sent_match, raw_match)

    return processed_sent

def preprocess(sents: List[str], lang: str) -> List[str]:
    """
    Preprocess a batch of input sentences for the translation.
    
    Args:
        sents (List[str]): batch of input sentences to preprocess.
        lang (str): language code of the input sentences.
        
    Returns:
        List[str]: preprocessed batch of input sentences.
    """
    lang = iso_to_flores[lang]

    # -------------------------------------------------------
    # normalize punctuations
    with tempfile.TemporaryDirectory() as tmpdirname:
        inpath = os.path.join(tmpdirname, "tmp.txt")
        outpath = inpath.replace("tmp.txt", 'tmp_norm.txt')
        with open(inpath, "w", encoding="utf-8") as f:
            f.write("\n".join(sents))
        
        os.system(f"bash {CURRENT_DIRECTORY}/normalize_punctuation.sh {lang} < {inpath} > {outpath}")
        
        with open(outpath, "r", encoding="utf-8") as f:
            sents = f.read().split("\n")
    # -------------------------------------------------------

    if lang == "eng_Latn":
        processed_sents = [
            preprocess_sent(sent, None, lang) for sent in sents
        ]
    else:
        normalizer = normfactory.get_normalizer(flores_codes[lang])

        processed_sents = [
            preprocess_sent(sent, normalizer, lang) for sent in sents
        ]
    
    return processed_sents

def postprocess(
    sents: List[str],
    lang: str,
    vocab_processor: spm.SentencePieceProcessor,
    common_lang: str = "hin_Deva",
    original_sents: List[str] = None
) -> List[str]:
    """
    Postprocesses a batch of input sentences after the translation generations.
    
    Args:
        sents (List[str]): batch of translated sentences to postprocess.
        lang (str): flores language code of the input sentences.
        common_lang (str, optional): flores language code of the transliterated language (defaults: hin_Deva).
        
    Returns:
        List[str]: postprocessed batch of input sentences.
    """
    if vocab_processor:
        sents = [vocab_processor.decode(x.split(" ")) for x in sents]
    
    lang = iso_to_flores[lang]
    postprocessed_sents = []
    
    if lang == "eng_Latn":
        for sent in sents:
            postprocessed_sents.append(en_detok.detokenize(sent.split(" ")))
    else:
        for sent in sents:
            outstr = indic_detokenize.trivial_detokenize(
                xliterator.transliterate(sent, flores_codes[common_lang], flores_codes[lang]), flores_codes[lang]
            )
            postprocessed_sents.append(outstr)
    
    if original_sents:
        # find the emails in the input sentences and then 
        # trim the additional spaces in the generated translations
        matches = [re.findall(EMAIL_PATTERN, x) for x in original_sents]
        
        for i in range(len(postprocessed_sents)):
            sent = postprocessed_sents[i]
            for match in matches[i]:
                potential_match = match.replace("@", "@ ")
                sent = sent.replace(potential_match, match)
            postprocessed_sents[i] = sent
    
    return postprocessed_sents
