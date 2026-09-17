import os
from infra.settings import get_settings, export_langsmith_env
export_langsmith_env(get_settings())
## 必须要加load_dotenv(),不然读取不到
# load_dotenv()
print("TRACING:", os.environ.get("LANGSMITH_TRACING"))
print("KEY:", os.environ.get("LANGSMITH_API_KEY", ""))
print("PROJECT:", os.environ.get("LANGSMITH_PROJECT"))