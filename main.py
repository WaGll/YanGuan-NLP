import pandas as pd
import logging
from logging.config import dictConfig
import config
from data_cleaner import DataCleaner
from text_analyzer import TextAnalyzer
from sentiment_analyzer import SentimentAnalyzer
from cluster_classifier import ClusterClassifier
from lda_modeler import LDAModeler
import matplotlib.pyplot as plt
import chardet

# 设置支持中文的字体，例如 SimHei（黑体）
plt.rcParams['font.family'] = 'SimHei'
# 解决负号显示问题
plt.rcParams['axes.unicode_minus'] = False

dictConfig(config.LOGGING_CONFIG)
logger = logging.getLogger(__name__)

def main():
    try:
        logger.info("开始读取数据...")
        # 读取源数据文件
        cleaner = DataCleaner(config)
        df = cleaner.load_and_clean_data()
        print(df['bigram_tokens'].head(15))

        logger.info("开始文本分析...")
        # 实例化 TextAnalyzer 类
        text_analyzer = TextAnalyzer(df)
        text_analyzer.generate_topic_wordcloud()
        text_analyzer.generate_top15_word_frequency_chart()
        # text_analyzer.contribution_network_analysis()

        logger.info("开始情感分析...")
        # 实例化 SentimentAnalyzer 类
        sentiment_analyzer = SentimentAnalyzer(df)
        sentiment_analyzer.snow_analysis()
        sentiment_analyzer.optimize_with_ml()
        sentiment_analyzer.plot_sentiment_distribution()

        logger.info("聚类分析...")
        # 实例化 ClusterClassifier 类
        cluster_classifier = ClusterClassifier(df)
        cluster_classifier.unified_clustering(method='kmeans')
        cluster_classifier.classify_motivation()

        # 绘制箱线图，此时 cluster 列已经存在
        sentiment_analyzer.plot_boxplot()

        # logger.info("开始LDA建模...")
        # lda_modeler = LDAModeler(df['bigram_tokens'])
        # best_k = lda_modeler.select_topics(2, 6)
        # lda_modeler.train(best_k)
        # lda_modeler.explain_topics()
        # lda_modeler.save_topics_to_csv()  # 保存主题到CSV文件
        logger.info("分析完成！")
    except FileNotFoundError:
        logger.error("文件未找到，请检查文件路径。")
    except pd.errors.ParserError:
        logger.error("数据解析错误，请检查数据格式。")
    except Exception as e:
        logger.error(f"分析失败: {str(e)}", exc_info=True)

if __name__ == "__main__":
    main()