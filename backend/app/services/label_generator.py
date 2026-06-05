"""
主题标签生成器

基于领域关键词映射表，对每个主题的 Top-N 关键词进行加权匹配评分，
自动生成有业务含义的主题名称（business_label），替代原始的关键词拼接标签。

算法:
  1. 对每个领域 D，计算加权匹配分数: score(D) = Σ (1/rank_i^1.5)
     使用指数衰减确保排名靠前的关键词主导匹配
  2. 按 score 降序排列领域
  3. 如果 top_score ≥ 2× second_score → 直接使用 top 领域标签
  4. 如果 second 接近 top → "{top_short}与{second_short}"
  5. 如果 top_score < 阈值 → 回退到 "{top_keyword}相关"
"""

import logging

logger = logging.getLogger(__name__)


class TopicLabelGenerator:
    """基于领域词典自动生成业务主题标签。

    纯函数设计（@classmethod），无状态，不需要数据库会话。
    输入 Topic Top-N 关键词列表，输出业务标签字符串。

    领域词典设计原则:
    - 只收录具有领域辨识力的关键词
    - 过于通用的词（如"基础""强化""时间""月份"）不加入任何领域
    - 当一个词出现在多个领域中时，按 DOMAINS 顺序优先匹配
    """

    # ── 领域关键词映射表 ──
    # 顺序有意义：更具体的领域排在前面，匹配时优先消耗关键词
    DOMAINS: list[tuple[str, set[str]]] = [
        # --- 学科领域（最具体，排最前）---
        ("英语备考", {
            "英语", "阅读", "单词", "作文", "翻译", "完形", "长难句",
            "语法", "词汇", "英一", "英二", "英语一", "英语二",
        }),
        ("数学复习", {
            "数学", "张宇", "武忠祥", "李永乐", "王式安", "方浩", "余丙森",
            "数一", "数二", "数三", "高数", "线代", "概率论", "数理统计",
        }),
        ("政治复习", {
            "政治", "徐涛", "肖秀荣", "背诵", "时政", "马原", "毛概", "思修",
        }),
        ("专业课", {
            "专业课", "统计学", "茆诗松", "贾俊平", "应用统计", "应统",
            "专业课程", "432", "432考研", "396考研",
        }),

        # --- 考研生命周期（具体流程）---
        ("调剂与复试", {
            "调剂", "复试", "面试", "第二轮", "二次录取",
        }),
        ("上岸与录取", {
            "上岸", "录取", "考上", "被录取", "通过",
        }),
        ("报考流程", {
            "初试", "报名", "国家线", "确认", "第一轮", "报考", "考试",
        }),

        # --- 心理/规划维度 ---
        ("备考心态", {
            "紧张", "焦虑", "压力", "放松", "心态", "崩溃", "迷茫",
            "冷静", "平常心", "淡定", "坚持",
        }),
        ("院校选择", {
            "择校", "双非", "一本", "二本", "院校", "学校", "志愿",
        }),
        ("备考规划", {
            "一战", "二战", "三战", "计划", "进度", "阶段", "暑假", "寒假",
            "来得及", "规划", "安排",
        }),

        # --- 学习行为 ---
        ("刷题练习", {
            "刷题", "做题", "练习", "习题", "试卷", "模拟",
        }),
        ("学习资源", {
            "资料", "视频", "网盘", "教材", "真题", "笔记", "课件", "书籍",
            "资源", "链接", "分享", "求",
        }),

        # --- 教学/师资 ---
        ("师资课程", {
            "老师", "授课", "教学", "讲解", "课堂", "导师", "机构",
            "文登", "海文", "新东方", "启航", "高途", "报班",
        }),

        # --- 社交/互动 ---
        ("社交互动", {
            "感谢", "谢谢", "许愿", "还愿", "打卡", "鼓励", "害人", "顶上去",
            "弹幕", "三连", "点赞", "收藏", "关注",
        }),

        # --- 新增领域 ---
        ("数据工具", {
            "Python", "python", "Excel", "excel", "SPSS", "spss", "SQL", "sql",
            "R语言", "数据分析", "数据科学", "可视化", "编程", "代码",
            "软件", "工具", "平台", "系统",
        }),
        ("跨考讨论", {
            "跨考", "跨专业", "跨学校", "跨地区", "三跨", "转专业",
            "转行", "改行", "非本专业", "零基础",
        }),
        ("择校理由", {
            "实力", "难度", "竞争", "性价比", "认可度", "含金量",
            "招生", "名额", "报考人数", "报录比", "分数线",
        }),
        ("毕业去向", {
            "毕业", "就业", "工作", "薪资", "薪水", "待遇",
            "发展前景", "就业率", "出路", "行业", "岗位", "招聘",
        }),
        ("考试技巧", {
            "技巧", "方法", "策略", "高效", "速成", "捷径",
            "思路", "解题", "大题", "选择题", "得分", "拿分",
        }),
        ("经验分享", {
            "经验", "分享", "建议", "教训", "踩坑", "误区",
            "体会", "心得", "总结", "过来人", "推荐", "避坑",
        }),
    ]

    # ── 领域标签缩写映射（用于组合标签时取核心词）──
    DOMAIN_SHORT: dict[str, str] = {
        "英语备考": "英语",
        "数学复习": "数学",
        "政治复习": "政治",
        "专业课": "专业课",
        "调剂与复试": "复试",
        "上岸与录取": "上岸",
        "报考流程": "报考",
        "备考心态": "心态",
        "院校选择": "择校",
        "备考规划": "备考",
        "刷题练习": "刷题",
        "学习资源": "资源",
        "师资课程": "师资",
        "社交互动": "互动",
        "数据工具": "工具",
        "跨考讨论": "跨考",
        "择校理由": "择校",
        "毕业去向": "就业",
        "考试技巧": "技巧",
        "经验分享": "经验",
    }

    # ── 关键词到领域的快速查找索引（类加载时构建）──
    _keyword_to_domain: dict[str, str] = {}

    @classmethod
    def _build_index(cls) -> None:
        """构建关键词→领域查找索引（仅首次调用时构建）。"""
        if cls._keyword_to_domain:
            return
        for domain_label, keywords in cls.DOMAINS:
            for kw in keywords:
                # 如果同一个词出现在多个领域中，第一个胜出（DOMAINS 顺序有意义）
                if kw not in cls._keyword_to_domain:
                    cls._keyword_to_domain[kw] = domain_label

    @classmethod
    def generate(cls, keywords: list[tuple[str, float, int]]) -> str:
        """基于主题 Top-N 关键词生成业务标签。

        Args:
            keywords: [(word, weight, rank), ...]，rank 从 1 开始

        Returns:
            业务标签字符串，如 "数学复习"、"心态与英语"
        """
        cls._build_index()

        if not keywords:
            return "未分类"

        # 1. 计算各领域加权匹配分数（指数衰减，排名靠前权重更高）
        domain_scores = cls._score_domains(keywords)

        # 2. 按分数降序排列
        sorted_domains = sorted(domain_scores.items(), key=lambda x: x[1], reverse=True)

        if not sorted_domains or sorted_domains[0][1] < 0.1:
            # 无显著领域匹配 → 回退到首个关键词
            return f"{keywords[0][0]}相关"

        top_domain, top_score = sorted_domains[0]

        # 3. 确定第二领域（跳过与 top 相同的缩写）
        second_domain, second_score = ("", 0.0)
        top_short = cls.DOMAIN_SHORT.get(top_domain, top_domain)
        for d, s in sorted_domains[1:]:
            d_short = cls.DOMAIN_SHORT.get(d, d)
            # 跳过冗余（如 "备考心态" 和 "备考规划" 的 short 分别是 "心态" 和 "备考"，不冲突）
            if d_short != top_short:
                second_domain, second_score = d, s
                break

        # 4. 标签生成规则
        # 规则 a: top 显著领先 (≥ 2.0x) → 直接用 top 标签
        if second_score == 0.0 or top_score >= second_score * 2.0:
            return top_domain

        # 规则 b: top 与 second 接近 → 组合标签（使用缩写形式避免冗余）
        second_short = cls.DOMAIN_SHORT.get(second_domain, second_domain)

        # 避免语义冗余组合
        if top_short in second_short or second_short in top_short:
            return top_domain

        combined = f"{top_short}与{second_short}"

        # 长度限制：≤ 8 字符
        if len(combined) > 8:
            return top_domain

        return combined

    @classmethod
    def _score_domains(
        cls, keywords: list[tuple[str, float, int]]
    ) -> dict[str, float]:
        """计算各领域匹配分数。

        使用 rank^1.5 倒数加权：
        - rank 1 → 1.000, rank 2 → 0.354, rank 3 → 0.192
        - rank 5 → 0.089, rank 8 → 0.044, rank 10 → 0.032

        同一关键词只计入第一个匹配到的领域（避免重复计数）。

        Returns:
            {domain_label: score, ...}
        """
        scores: dict[str, float] = {}
        used_words: set[str] = set()

        for word, _weight, rank in keywords:
            if word in used_words:
                continue
            domain = cls._keyword_to_domain.get(word)
            if domain is None:
                continue
            used_words.add(word)
            rk = float(max(rank, 1))
            scores[domain] = scores.get(domain, 0.0) + (1.0 / (rk ** 1.5))

        return scores
