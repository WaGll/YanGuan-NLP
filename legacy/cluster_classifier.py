import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
import hdbscan
import os

class ClusterClassifier:
    def __init__(self, df):
        self.df = df
        self.image_folder = 'images'
        if not os.path.exists(self.image_folder):
            os.makedirs(self.image_folder)

    def unified_clustering(self, method='kmeans'):
        """统一聚类接口"""
        if method == 'kmeans':
            self._kmeans_analysis()
        elif method == 'hdbscan':
            self._hdbscan_analysis()

    def _kmeans_analysis(self):
        """KMeans聚类分析"""
        kmeans = KMeans(n_clusters=3)
        self.df['cluster'] = kmeans.fit_predict(self.df[['sentiment']])

    def _hdbscan_analysis(self):
        """HDBSCAN聚类分析"""
        hdbscan_model = hdbscan.HDBSCAN(min_cluster_size=5)
        self.df['cluster'] = hdbscan_model.fit_predict(self.df[['sentiment']])

    def classify_motivation(self):
        """备考动机分类"""
        # 使用已有聚类结果进行解释
        sns.boxplot(x='cluster', y='sentiment', data=self.df)
        save_path = os.path.join(self.image_folder, 'motivation_classification.png')
        plt.savefig(save_path)
        plt.close()