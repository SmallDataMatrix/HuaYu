# HuaYu · SmallDataMatrix Portfolio

A multi-page Streamlit app combining two badminton data tools, deployed at [small-data-matrix.com](https://small-data-matrix.com).

## Pages

| Page | Description |
|------|-------------|
| **Home** | Resume / portfolio landing page |
| **Pose Recognition** | Upload a badminton video → pose overlay, stroke detection, landing map, joint-angle charts |
| **VOC Mining** | Enter a racket name → crawl Bilibili danmaku & comments → LLM opinion analysis |

## Local development

```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Required for VOC page
cp .env.example .env
# Edit .env and set DEEPSEEK_API_KEY=<your-key>

streamlit run Home.py
```

## Deployment (Streamlit Community Cloud)

1. Push this repo to GitHub.
2. Go to [share.streamlit.io](https://share.streamlit.io) → **New app** → select this repo, branch `main`, main file `Home.py`.
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

## Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DEEPSEEK_API_KEY` | Yes (VOC page) | DeepSeek API key for LLM opinion mining |
| `BILI_SESSDATA` | No | Bilibili session cookie for higher crawl limits |
