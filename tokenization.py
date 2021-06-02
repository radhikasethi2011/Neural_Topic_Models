import re
from typing import List
from collections import defaultdict
import multiprocessing

from tqdm import tqdm

from pyhanlp import *
import spacy

LANG_CLS = defaultdict(lambda:"SpacyTokenizer")
LANG_CLS.update({
    "en": "SpacyTokenizer",
})

SPACY_MODEL = {
    "en": "en_core_web_sm",
    "ja": "ja_core_news_sm"
}

        
class SpacyTokenizer(object):
    def __init__(self, lang="en", stopwords=None):
        self.stopwords = stopwords
        self.nlp = spacy.load(SPACY_MODEL[lang], disable=['ner', 'parser'])
        print("Using SpaCy tokenizer YES")

        
    def tokenize(self, lines: List[str]) -> List[List[str]]:
        docs = self.nlp.pipe(lines, batch_size=500, n_process=multiprocessing.cpu_count())
        docs = [[token.lemma_ for token in doc if not (token.is_stop or token.is_punct)] for doc in docs]
        return docs
        

if __name__ == '__main__':
    tokenizer=SpacyTokenizer()
    #print(tokenizer.tokenize('qwertyuiop./asdfghjkl@#$^&')
  
