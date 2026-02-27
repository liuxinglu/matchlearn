# MatchLearn - 智能人岗匹配与学习助手

MatchLearn 是一个基于 AI 的职业发展辅助工具，旨在帮助求职者分析简历与目标职位的差距，并生成个性化的学习计划，最终通过学习成果反向优化简历。

## 核心功能

1.  **简历 & JD 解析**：支持 PDF 简历上传和职位描述（JD）文本输入，使用 LLM 提取关键信息。
2.  **人岗匹配分析 (Gap Analysis)**：
    *   智能分析技能匹配度，生成多维度雷达图。
    *   识别关键技能缺失，并按优先级排序。
3.  **个性化学习计划**：
    *   针对缺失技能，自动生成学习任务。
    *   一键搜索慕课网 (Imooc) 和 B站 (Bilibili) 的优质中文学习资源。
4.  **学习成果闭环**：
    *   完成学习任务后，系统自动生成简历优化建议。
    *   一键将学习成果（项目经验/技能）同步更新到简历数据库。
    *   实时预览优化后的简历效果。

## 技术栈

*   **Frontend**: Next.js 14, React, Tailwind CSS, Shadcn/ui, Framer Motion, Recharts
*   **Backend**: FastAPI, SQLAlchemy, SQLite (Async), Pydantic
*   **AI**: DeepSeek V3 (via OpenAI Compatible API)

## 快速开始

### 1. 环境准备

确保已安装 Python 3.10+ 和 Node.js 18+。

### 2. 后端启动

```bash
# 进入后端目录
cd backend

# 创建虚拟环境
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
# 在 backend 目录下创建 .env 文件，填入您的 DeepSeek API Key
# DEEPSEEK_API_KEY=sk-xxxxxxxx

# 初始化数据库
python init_db.py

# 启动服务
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

### 3. 前端启动

```bash
# 进入前端目录
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

打开浏览器访问 `http://localhost:3000` 即可使用。

## 使用流程

1.  **上传简历**：在左侧面板上传您的 PDF 简历。
2.  **输入 JD**：粘贴您想应聘的目标职位描述。
3.  **点击分析**：系统将生成匹配度报告和技能雷达图。
4.  **开始学习**：点击差距分析中的“开始学习”，系统会自动为您创建学习任务并搜索教程。
5.  **查看计划**：在“我的学习计划”中查看进行中的任务。
6.  **完成任务**：学习完成后，点击任务旁的“打勾”按钮。
7.  **更新简历**：确认系统的优化建议，您的简历将自动更新。
8.  **预览效果**：在底部的“简历预览”中查看新增的项目经历和技能。

## License

MIT
