import os
import streamlit as st

# Streamlit Cloud stores secrets in st.secrets; surface them as env vars
# so llm/deepseek.py can pick up DEEPSEEK_API_KEY via os.getenv().
try:
    for _k, _v in st.secrets.items():
        if isinstance(_v, str):
            os.environ.setdefault(_k, _v)
except Exception:
    pass

pg = st.navigation(
    [
        st.Page("pages/home.py", title="致华羽", default=True),
        st.Page("pages/cv.py", title="简历"),
        st.Page("pages/pose_recognition.py", title="辅助教学分析"),
        st.Page("pages/voc.py", title="VOC 用户评价监测"),
    ]
)
pg.run()
