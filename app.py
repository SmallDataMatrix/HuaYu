import streamlit as st

pg = st.navigation(
    [
        st.Page("pages/home.py", title="致华羽", default=True),
        st.Page("pages/cv.py", title="简历"),
        st.Page("pages/pose_recognition.py", title="辅助教学分析"),
        st.Page("pages/voc.py", title="VOC 用户评价监测"),
    ]
)
pg.run()
