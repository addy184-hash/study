import os

# DeepSeek API 配置（国内直连，不需要翻墙）
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"

# 如果你用通义千问，改成：
# DEEPSEEK_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
# DEEPSEEK_MODEL = "qwen-plus"
