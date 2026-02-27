# LLM Prompts

PARSE_RESUME_PROMPT = """
You are an expert resume parser. Extract the following information from the resume text below and return it in valid JSON format.

Fields to extract:
- name: string (or "Unknown")
- email: string (or "Unknown")
- skills: list of strings (technical skills, programming languages, tools)
- education: list of objects (degree, school, year)
- experience: list of objects (title, company, duration, description)
- projects: list of objects (name, description, technologies used)

Resume Text:
{resume_text}

Return ONLY the JSON object. Do not include any markdown formatting or explanations.
"""

PARSE_JD_PROMPT = """
You are an expert HR assistant. Extract the required skills and qualifications from the Job Description (JD) text below and return it in valid JSON format.

Fields to extract:
- title: string
- company: string (or "Unknown")
- required_skills: list of strings (must-have skills)
- nice_to_have_skills: list of strings
- responsibilities: list of strings
- education_requirements: string

JD Text:
{jd_text}

Return ONLY the JSON object. Do not include any markdown formatting or explanations.
"""

ANALYZE_GAP_PROMPT = """
You are a career coach expert. Compare the following Resume and Job Description (JD) to perform a gap analysis.

Resume:
{resume_json}

Job Description:
{jd_json}

{completed_courses}

**重要指导原则：**
1. **技能关联性判断**：如果用户已经掌握了基础技能（如Python、Java等编程语言），那么相关的框架、工具和技术（如Spring Cloud、Kubernetes、数据库等）应该视为用户已经具备学习基础。
2. **推荐类型判断**：
   - 如果用户已经完成了**完全相同技能**的课程，推荐**实践项目**
   - 如果用户已经掌握了**相关基础技能**（如Python → 后端框架），推荐**实践项目**
   - 如果用户完全没有相关基础，推荐**学习课程**
3. **实践项目推荐**：应该具体、可操作，包括项目类型、技术栈、实现思路、预期成果等。
4. **学习课程推荐**：针对完全陌生的技能，推荐系统的学习资源。

**技能关联示例**：
- Python → Django/Flask/FastAPI/后端开发 → 推荐实践项目
- Java → Spring/Spring Boot/Spring Cloud → 推荐实践项目
- 编程基础 → 数据库/缓存/消息队列 → 推荐实践项目
- 完全陌生的领域（如AI、区块链） → 推荐学习课程

Provide the analysis in the following JSON format. Please ensure all text content (summary, recommendations, etc.) is in **Simplified Chinese**.
{{
    "overall_score": float (0-100),
    "radar_data": {{
        "Languages": int (0-100),
        "Frameworks": int (0-100),
        "Tools": int (0-100),
        "Experience": int (0-100),
        "Soft Skills": int (0-100)
    }},
    "gap_details": [
        {{
            "missing_skill": string,
            "importance": string (High/Medium/Low),
            "recommendation": string (specific advice. 根据技能关联性判断：如果用户已经掌握相关基础技能，推荐具体的实践项目（包括项目类型、技术栈、实现步骤）；否则推荐系统的学习资源如Imooc (慕课网)或Bilibili (B站)),
            "recommendation_type": string ("course" or "project")  # "course" for learning resources, "project" for practical projects
        }}
    ],
    "summary": string (a brief summary of the match in Chinese)
}}

Return ONLY the JSON object.
"""

GENERATE_RESUME_CONTENT_PROMPT = """
The user has completed a learning task: "{course_title}".
Task description/Goal: "{task_description}".

Please generate a professional resume bullet point (1-2 sentences) that the user can add to their resume to showcase this new skill.
The tone should be professional, action-oriented, and result-driven.

Return ONLY the text string.
"""
