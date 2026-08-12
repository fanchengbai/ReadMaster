# ReadMaster 软件设计文档


## 1. 系统目标

ReadModel 是一个以英文阅读为核心的学习系统。

用户通过阅读真实英文内容，
逐渐提高：

- 词汇能力
- 长句理解能力
- 阅读速度
- 专业领域阅读能力


---

# 2. 系统流程


导入书籍

↓

文本解析

↓

阅读页面

↓

点击未知单词

↓

查看词汇信息

↓

加入生词库

↓

完成章节阅读

↓

生成训练任务

↓

学习检测

↓

进入下一章节



---

# 3. 系统模块


## Reader

负责：

- 文档加载
- 页面显示
- 双语切换
- 单词定位


## Dictionary

负责：

- 单词数据
- 词根
- 词族
- 释义


## Vocabulary Manager

负责：

- 用户生词
- 学习状态
- 复习计划


## Question Engine

负责：

根据词汇生成：

- 选择题
- 填空题
- 拼写题
- 语境题


## AI Service

负责：

- 复杂解释
- 句子分析
- 动态生成内容



---

# 4. 数据模型


Book

    |
    Chapter

        |
        Page

            |
            Sentence

                |
                Word


Word:

- word
- pronunciation
- meaning
- root
- examples


UserWord:

- word_id
- familiarity
- wrong_count
- review_time


Question:

- type
- content
- answer
- difficulty


---

# 5. 第一版本目标


实现：

[x] 导入TXT

[x] 导入EPUB

[x] 英文阅读

[x] 章节切换与阅读进度恢复

[x] 点击查询单词

[x] 保存生词

[x] 简单刷题


暂不实现：

- 复杂AI
- 大模型训练
- 在线社区


---

# 6. 后续方向


最终目标：

建立个人英语语言模型。


用户不是学习单词，

而是在建立：

自己的英文世界理解能力。
