import re
import jieba
from gensim.models.phrases import Phrases
import config
import chardet
import os
import pandas as pd

class DataCleaner:
    def __init__(self, config):
        self.stopwords = self._load_stopwords(config.STOPWORDS_PATH)
        jieba.load_userdict(config.CUSTOM_DICT_PATH)
        self.synonyms = self._load_synonyms(config.SYNONYM_PATH)
        self.data_file_path = config.data_file_path

    def _load_file(self, path):
        """
        通用的文件读取和编码处理函数
        :param path: 文件路径
        :return: 解码后的文本
        """
        with open(path, 'rb') as f:
            raw_data = f.read()
        detected_encoding = chardet.detect(raw_data)['encoding']
        return raw_data.decode(detected_encoding, errors='replace')

    def _load_stopwords(self, path):
        """加载停用词表"""
        content = self._load_file(path)
        return set(content.splitlines()).union(config.ADDITIONAL_STOPWORDS)

    def _load_synonyms(self, path):
        """加载同义词字典"""
        synonyms = {}
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith('#'):
                    continue
                words = line.strip().split(',')
                if len(words) > 1:
                    for word in words[1:]:
                        if word:
                            synonyms[word] = words[0]
        return synonyms

    def clean_text(self, text):
        """文本清洗管道"""
        text = re.sub(r'http\S+|www\S+', '', str(text))
        text = re.sub(r'[\x00-\x1F\u200b#【】]', '', str(text))
        text = re.sub(r'\b(?:一下|这个|那种)\b', '', text)
        return text.strip()

    def tokenize(self, text):
        """分词处理"""
        tokens = [word for word in jieba.lcut(text) if word not in self.stopwords and len(word) > 1]
        # 替换同义词
        replaced_tokens = [self.synonyms.get(token, token) for token in tokens]
        return replaced_tokens

    def build_bigrams(self, tokens_list):
        """短语挖掘"""
        bigram_model = Phrases(tokens_list, min_count=20, threshold=50)
        return [
            [word.replace('_', ' ') for word in bigram_model[doc]]
            for doc in tokens_list
        ]

    def load_and_clean_data(self):
        """加载并清洗数据"""
        content = self._load_file(self.data_file_path)
        temp_file = 'temp_comment.csv'
        with open(temp_file, 'w', encoding='utf-8') as f:
            f.write(content)
        df = pd.read_csv(temp_file, usecols=["content"])
        os.remove(temp_file)  # 删除临时文件
        df = df.dropna()
        df = df.drop_duplicates()
        df['cleaned'] = df['content'].apply(self.clean_text)
        df['tokens'] = df['cleaned'].apply(self.tokenize)
        df['bigram_tokens'] = self.build_bigrams(df['tokens'].tolist())
        return df