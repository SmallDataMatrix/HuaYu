# HuaYu · SmallDataMatrix Portfolio

A multi-page Streamlit app combining two badminton data tools, deployed at [small-data-matrix.com](https://small-data-matrix.com).

## Pages

| Page | Description |
|------|-------------|
| **致华羽** | Cover letter / portfolio landing page |
| **简历** | CV page with embedded PDF download |
| **辅助教学分析** | Upload a badminton video → pose overlay, stroke detection, landing map, joint-angle charts |
| **VOC 用户评价监测** | Enter a racket name → crawl Bilibili danmaku & comments → LLM opinion analysis |

## Local development

```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Deployment (Streamlit Community Cloud)

1. Push this repo to GitHub (the CV PDF and seed VOC data are tracked — no extra steps needed).
2. Go to [share.streamlit.io](https://share.streamlit.io) → **New app** → select this repo, branch `main`, main file **`streamlit_app.py`**.
3. Under **Advanced settings → Secrets**, add:
   ```toml
   DEEPSEEK_API_KEY = "sk-..."
   ```
4. Deploy. Once live, go to **Settings → Custom domain** and enter `small-data-matrix.com`.
5. In your DNS provider, add a CNAME record:
   ```
   small-data-matrix.com  →  custom-domains.streamlit.app
   ```
   SSL is provisioned automatically within a few minutes to hours.

### Data persistence notes

- **CV PDF** (`data/Kexin_Wang_CV_CN.pdf`) is committed to the repo and always available.
- **VOC search history** is written to disk within the container lifetime and cached in session state. A seed result for 华羽屠夫 is committed and loads instantly without a crawl. New searches persist until the container restarts; write failures are logged and swallowed so the app never crashes.

## Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DEEPSEEK_API_KEY` | Yes (VOC page) | DeepSeek API key for LLM opinion mining |
| `BILI_SESSDATA` | No | Bilibili session cookie for higher crawl limits |
