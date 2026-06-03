import os

# 停用词表路径
STOPWORDS_PATH = os.path.join('data', 'merged_stopwords.txt')

# 自定义字典路径
CUSTOM_DICT_PATH = os.path.join('data', '自定义字典.txt')

# 同义词字典路径
SYNONYM_PATH = os.path.join('data', '同义词.txt')

data_file_path = os.path.join('data', '毕业去向讨论.csv')

# 额外的停用词
ADDITIONAL_STOPWORDS = set([
    '这个', '一下','doge', '大哭', '这个', '一下', '没有', '真的', '时候', 'call',
    '问题', '应该', '这样', '但是', '还是', '或者', '为啥', '不是',
    '是不是', '很多', '东西', '怎么', '如何', '请问', '可以', '需要',
    '就是', '感觉', '可能', '一定', '不能', '想要', '终于', '添加',
    '脱单', '金箍', '已三连求', 'tv', '星星', '已三连', '热词 系列', '委屈',
    '微笑', '吃瓜', '哈哈哈', '实验报告', '运行', '安装', '投币',
    '三连', '大佬', '有没有', '入门', '喜欢', '谢谢', '感谢',
    '文件', '分享', '模式', '创建', '运行', '打开','PDF','xdm','TM','时间',
    '星星','xx','群满','app'
])

# 日志配置
LOGGING_CONFIG = {
    'version': 1,
    'handlers': {
        'file': {
            'class': 'logging.FileHandler',
            'filename': 'analysis.log',
            'formatter': 'detailed'
        },
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        }
    },
    'formatters': {
        'detailed': {
            'format': '%(asctime)s - %(levelname)s - %(module)s - %(message)s'
        },
        'simple': {
            'format': '%(levelname)s - %(message)s'
        }
    },
    'root': {
        'handlers': ['file', 'console'],
        'level': 'INFO'
    }
}