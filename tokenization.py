import re
from typing import List
from collections import defaultdict
import multiprocessing

from tqdm import tqdm

from pyhanlp import *
import spacy

LANG_CLS = defaultdict(lambda:"SpacyTokenizer")
LANG_CLS.update({
    "zh": "HanLPTokenizer",
    "en": "SpacyTokenizer",
})

SPACY_MODEL = {
    "en": "en_core_web_sm",
    "ja": "ja_core_news_sm"
}


class HanLPTokenizer(object):
    def __init__(self, stopwords=None):
        print("Using HanLP tokenizer")
        
    def tokenize(self, lines: List[str]) -> List[List[str]]:
        docs = []
        for line in tqdm(lines):
            tokens = [t.split(' ') for t in tokens]
            docs.append(tokens)
        return docs
        
        

if __name__ == '__main__':
    tokenizer=HanLPTokenizer()
    print(tokenizer.tokenize(['他拿的是《红楼梦》？！我还以为他是个Foreigner———']))
