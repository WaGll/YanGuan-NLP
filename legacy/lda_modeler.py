from gensim import corpora, models
import pyLDAvis.gensim_models as gensimvis
import pyLDAvis
import matplotlib.pyplot as plt
from gensim.models import CoherenceModel
import pandas as pd
import os
class LDAModeler:
    def __init__(self, texts):
        self.texts = texts
        self.dictionary = corpora.Dictionary(texts)
        self.corpus = [self.dictionary.doc2bow(text) for text in texts]
        self.image_folder = 'images'
        if not os.path.exists(self.image_folder):
            os.makedirs(self.image_folder)

    def select_topics(self, min_topics, max_topics):
        """选择最佳主题数"""
        perplexities = []
        coherences = []
        for num_topics in range(min_topics, max_topics + 1):
            lda_model = models.LdaModel(corpus=self.corpus,
                                        id2word=self.dictionary,
                                        num_topics=num_topics,
                                        passes=15,
                                        random_state=42)
            perplexities.append(lda_model.log_perplexity(self.corpus))
            coherence_model_lda = CoherenceModel(model=lda_model, texts=self.texts, dictionary=self.dictionary,
                                                 coherence='c_v')
            coherences.append(coherence_model_lda.get_coherence())

        # 绘制困惑度和一致性曲线
        self._plot_metrics(perplexities, coherences, min_topics, max_topics)

        # 选择最佳主题数
        best_k = coherences.index(max(coherences)) + min_topics
        return best_k

    def _plot_metrics(self, perplexities, coherences, min, max):
        """可视化困惑度和一致性"""
        x = range(min, max + 1)
        plt.figure(figsize=(12, 6))
        plt.subplot(1, 2, 1)
        plt.plot(x, perplexities)
        plt.xlabel('主题数')
        plt.ylabel('困惑度')
        plt.title('困惑度随主题数变化')
        plt.subplot(1, 2, 2)
        plt.plot(x, coherences)
        plt.xlabel('主题数')
        plt.ylabel('一致性')
        plt.title('一致性随主题数变化')
        new_save_path = os.path.join(self.image_folder, 'LDA困惑度和一致性图.png')
        plt.savefig(new_save_path)
        plt.close()

    def train(self, num_topics):
        """模型训练"""
        self.lda = models.LdaModel(
            corpus=self.corpus,
            id2word=self.dictionary,
            num_topics=num_topics,
            passes=50,
            alpha='auto'
        )

    def explain_topics(self):
        """主题解释"""
        vis = gensimvis.prepare(self.lda, self.corpus, self.dictionary)
        pyLDAvis.save_html(vis, 'topic_visual.html')

    def save_topics_to_csv(self, num_words=10):
        """将主题保存为CSV文件"""
        topics = self.lda.print_topics(num_words=num_words)
        data = []
        for topic_id, topic in topics:
            words = topic.split('+')
            word_list = []
            for word in words:
                prob, w = word.split('*')
                word_list.append(w.strip().replace('"', ''))
            data.append([topic_id, ', '.join(word_list)])

        df = pd.DataFrame(data, columns=['Topic ID', 'Top Words'])
        df.to_csv('lda_topics.csv', index=False)