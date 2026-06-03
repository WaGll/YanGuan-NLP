import pandas as pd
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import networkx as nx
import plotly.graph_objects as go
import os

class TextAnalyzer:
    def __init__(self, df):
        self.df = df
        self.image_folder = 'images'
        if not os.path.exists(self.image_folder):
            os.makedirs(self.image_folder)
        self._token_frequency = None  # 缓存词频数据

    def _get_token_frequency(self):
        """获取词频数据"""
        if self._token_frequency is None:
            all_tokens = [word for doc in self.df['bigram_tokens'] for word in doc]
            self._token_frequency = pd.Series(all_tokens).value_counts()
        return self._token_frequency

    def _plot_wordcloud(self, data, save_path):
        """可视化工具函数 - 生成词云"""
        text = ' '.join(data.index)
        wordcloud = WordCloud(font_path='simhei.ttf',
                              background_color='white',
                              width=800,
                              height=600).generate(text)
        plt.figure(figsize=(10, 8))
        plt.imshow(wordcloud, interpolation='bilinear')
        plt.axis('off')
        new_save_path = os.path.join(self.image_folder, save_path)
        plt.savefig(new_save_path)
        plt.close()

    def generate_topic_wordcloud(self):
        """生成讨论话题的词云图"""
        token_series = self._get_token_frequency()
        self._plot_wordcloud(token_series, 'topic_wordcloud.png')

    def generate_top15_word_frequency_chart(self):
        """统计前十五的出现词的频率并设计折线 - 直方图"""
        token_series = self._get_token_frequency().head(15)

        plt.figure(figsize=(12, 6))
        ax1 = plt.gca()
        ax1.bar(token_series.index, token_series.values)
        ax1.set_xlabel('词语', fontsize=12)
        ax1.set_ylabel('频率', fontsize=12)
        ax1.set_title('前十五词语频率统计', fontsize=14, fontweight="bold")
        ax1.tick_params(axis='x', rotation=45)

        ax2 = ax1.twinx()
        ax2.plot(token_series.index, token_series.values, color='red')
        ax2.set_ylabel('频率（折线）')

        save_path = os.path.join(self.image_folder, 'top15_word_frequency.png')
        plt.savefig(save_path)
        plt.close()

    def contribution_network_analysis(self):
        """贡献网络分析并可视化"""
        entities = []
        relationships = []
        for doc in self.df['bigram_tokens']:
            for i in range(len(doc) - 1):
                entity1 = doc[i]
                entity2 = doc[i + 1]
                entities.extend([entity1, entity2])
                relationships.append((entity1, entity2))

        # 构建图
        G = nx.Graph()
        G.add_nodes_from(set(entities))
        G.add_edges_from(relationships)

        # 生成节点位置
        pos = nx.spring_layout(G)

        # 准备节点数据
        node_x = []
        node_y = []
        node_text = []
        for node in G.nodes():
            x, y = pos[node]
            node_x.append(x)
            node_y.append(y)
            node_text.append(node)

        node_trace = go.Scatter(
            x=node_x, y=node_y,
            mode='markers+text',  # 显示节点和文字
            hoverinfo='text',
            text=node_text,  # 添加节点文字
            textposition='top center',  # 文字位置
            textfont=dict(size=8),  # 调整文字大小
            marker=dict(
                showscale=True,
                colorscale='YlGnBu',
                reversescale=True,
                color=[],
                size=10,
                colorbar=dict(
                    thickness=15,
                    title='Node Connections',
                    xanchor='left',
                    titleside='right'
                ),
                line_width=2))

        # 准备边数据
        edge_x = []
        edge_y = []
        for edge in G.edges():
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])

        edge_trace = go.Scatter(
            x=edge_x, y=edge_y,
            line=dict(width=0.5, color='#888'),
            hoverinfo='none',
            mode='lines')

        # 计算节点连接数
        node_adjacencies = []
        for node, adjacencies in enumerate(G.adjacency()):
            node_adjacencies.append(len(adjacencies[1]))
            node_trace.marker.color = node_adjacencies

        # 创建图形
        fig = go.Figure(data=[edge_trace, node_trace],
                        layout=go.Layout(
                            title='<br>贡献网络分析 - Plotly',
                            titlefont_size=16,
                            showlegend=False,
                            hovermode='closest',
                            margin=dict(b=20, l=5, r=5, t=40),
                            annotations=[dict(
                                text="",
                                showarrow=False,
                                xref="paper", yref="paper",
                                x=0.005, y=-0.002)],
                            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False))
                        )

        # 保存为 HTML 文件
        fig.write_html(os.path.join(self.image_folder, '贡献网络图.html'))

        return G