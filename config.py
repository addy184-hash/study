import os

# DeepSeek API 配置（国内直连，不需要翻墙）
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = "https://api.deepseek.com"

# 模型配置：
# - deepseek-chat: 基础对话模型，速度快，支持JSON结构化输出，用于技能拆解/资源推荐/计划生成
# - deepseek-reasoner: 推理模型(R1)，质量高，有思考链，用于普通问答和复杂问题
DEEPSEEK_MODEL = "deepseek-chat"
DEEPSEEK_REASONER_MODEL = "deepseek-reasoner"

# 如果你用通义千问，改成：
# DEEPSEEK_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
# DEEPSEEK_MODEL = "qwen-plus"
