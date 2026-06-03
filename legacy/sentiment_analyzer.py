import pandas as pd
from snownlp import SnowNLP
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import SVC
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_score, GridSearchCV
import matplotlib.pyplot as plt
import os
import numpy as np

plt.rcParams['font.sans-serif'] = ['SimHei']  # 全局设置中文显示
plt.rcParams['axes.unicode_minus'] = False

class SentimentAnalyzer:
    def __init__(self, df):
        self.df = df
        self.image_folder = 'images'
        if not os.path.exists(self.image_folder):
            os.makedirs(self.image_folder)

    def snow_analysis(self):
        """基础情感分析"""

        def handle_text(text):
            if pd.isna(text) or not isinstance(text, str) or len(text.strip()) == 0:
                return 0.5  # 对异常文本赋予中性情感分
            return SnowNLP(text).sentiments

        self.df['sentiment'] = self.df['cleaned'].apply(handle_text)

    def optimize_with_ml(self):
        """机器学习优化"""
        X = TfidfVectorizer().fit_transform(self.df['cleaned'])
        y = (self.df['sentiment'] > 0.6).astype(int)  # 二分类（后续可优化阈值）

        # 定义模型及参数网格
        models = {
            'SVM': {
                'model': SVC(),
                'params': {'C': [0.1, 1, 10], 'kernel': ['linear', 'rbf']}
            },
            'RandomForest': {
                'model': RandomForestClassifier(),
                'params': {'n_estimators': [50, 100, 200]}
            },
            'LogisticRegression': {
                'model': LogisticRegression(),
                'params': {'C': [0.1, 1, 10]}
            }
        }
        results = {}
        for name, config in models.items():
            grid_search = GridSearchCV(config['model'], config['params'], cv=5)
            grid_search.fit(X, y)
            results[name] = grid_search.best_score_

        # 可视化结果（优化颜色）
        plt.figure(figsize=(8, 5))
        bars = plt.bar(
            results.keys(), results.values(),
            color=['#4CAF50', '#2196F3', '#9C27B0'],  # 更鲜明的颜色
            edgecolor='black',  # 黑色边框
            linewidth=1.5,
            alpha=0.8  # 透明度
        )

        # 添加数据标签（带阴影效果）
        for bar in bars:
            height = bar.get_height()
            plt.text(
                bar.get_x() + bar.get_width() / 2.,
                height,
                f"{height:.2f}",
                ha="center",
                va="bottom",
                fontsize=10,
                bbox=dict(boxstyle="round", fc="white", ec="0.1", alpha=0.9)  # 标签背景框
            )
        plt.title("不同模型情感分析准确率对比", fontsize=14, fontweight="bold")
        plt.xlabel("模型", fontsize=12)
        plt.ylabel("准确率", fontsize=12)
        plt.ylim(0, 1)
        plt.grid(axis="y", linestyle="--", alpha=0.7)
        save_path = os.path.join(self.image_folder, 'sentiment_analysis_accuracy.png')
        plt.savefig(save_path)
        plt.close()

        return results

    def plot_sentiment_distribution(self):
        """生成情感分析图（分为消极、中性、积极三类）"""
        # 分类：<=0.3 消极，0.3<x<0.7 中性，>=0.7 积极
        self.df['sentiment_class'] = pd.cut(
            self.df['sentiment'],
            bins=[0, 0.3, 0.7, 1],
            labels=['消极', '中性', '积极']
        )
        class_counts = self.df['sentiment_class'].value_counts()

        plt.figure(figsize=(8, 5))
        bars = plt.bar(
            class_counts.index, class_counts.values,
            color=['#FF5722', '#3F51B5', '#4CAF50'],  # 更具情感隐喻的颜色
            edgecolor='white',
            linewidth=1.2,
            width=0.6  # 调整柱子宽度
        )

        # 添加数据标签（显示数量和百分比）
        total = class_counts.sum()
        for bar in bars:
            height = bar.get_height()
            plt.text(
                bar.get_x() + bar.get_width() / 2.,
                height,
                f"{height}\n({height/total:.1%})",
                ha="center",
                va="bottom",
                fontsize=10
            )

        plt.title("情感分类分布", fontsize=14, fontweight="bold")
        plt.xlabel("情感类别", fontsize=12)
        plt.ylabel("数量", fontsize=12)
        plt.grid(axis="y", linestyle="--", alpha=0.7)
        save_path = os.path.join(self.image_folder, 'sentiment_distribution.png')
        plt.savefig(save_path)
        plt.close()

    def plot_boxplot(self):
        """绘制箱线图"""
        plt.figure(figsize=(8, 5))
        data = [self.df[self.df['cluster'] == i]['sentiment'] for i in self.df['cluster'].unique()]
        colors = ['#FF9800', '#2196F3', '#4CAF50']  # 箱线图颜色
        boxes = plt.boxplot(
            data,
            patch_artist=True,
            tick_labels=self.df['cluster'].unique()  # 修改为 tick_labels
        )

        for patch, color in zip(boxes['boxes'], colors):
            patch.set_facecolor(color)
            patch.set_edgecolor('black')
            patch.set_linewidth(1.2)

        plt.title("不同聚类情感值分布", fontsize=14, fontweight="bold")
        plt.xlabel("cluster", fontsize=12)
        plt.ylabel("sentiment", fontsize=12)
        plt.grid(axis="y", linestyle="--", alpha=0.7)
        save_path = os.path.join(self.image_folder, 'sentiment_boxplot.png')
        plt.savefig(save_path)
        plt.close()
