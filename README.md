# ScholarMetrics

A Python-based research integrity analysis tool that calculates Research Integrity Measure (RIM) scores for scholars using Google Scholar data.

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd streamlit
pip install -r requirements.txt
```

### 2. Configure API Key

Create a `.env` file in the `streamlit` folder:

```bash
cd streamlit
cp .env.example .env
```

Edit `.env` and add your SerpAPI key:
```env
SERPAPI_KEY=your_key_here
UNPAYWALL_EMAIL=your_email@example.com
CURRENT_YEAR=2025
```

Get your free SerpAPI key at: https://serpapi.com/

### 3. Run the App

```bash
streamlit run app.py
```

Open http://localhost:8501 in your browser.

## 📊 Features

- 🔍 **Scholar ID Search** - Analyze any Google Scholar profile
- 📈 **RIM Score Calculation** - Research Integrity Measure (0-100)
- 📊 **Citation Analysis** - Log-normalized citation metrics
- 🔓 **Open Access Detection** - Via Unpaywall API
- ⚠️ **Retraction Detection** - Via Semantic Scholar
- 📥 **Excel Export** - Download complete analysis

## 🎯 RIM Score Interpretation

- **80-100**: Excellent research integrity
- **60-79**: Good research integrity  
- **40-59**: Fair research integrity
- **0-39**: Poor research integrity

## 🔬 How It Works

The app analyzes a scholar's top 10 publications and calculates RIM scores based on:

- **Citations (25%)** - Log-normalized citations per year
- **Journal Quality (20%)** - Placeholder (fixed at 50%)
- **Data Availability (15%)** - Open Access status
- **Relevance (20%)** - Retraction penalty
- **Funding (10%)** - Funding information present
- **Author Completeness (5%)** - Affiliation data quality
- **Peer Review (5%)** - Placeholder

## 🛠️ Tech Stack

- **Streamlit** - Web interface
- **Pandas** - Data processing
- **SerpAPI** - Google Scholar data
- **Crossref** - Publication metadata
- **Semantic Scholar** - Citation counts & retraction detection
- **Unpaywall** - Open Access status

## 📁 Project Structure

```
scholarmetrics/
├── streamlit/
│   ├── app.py              # Main Streamlit application
│   ├── requirements.txt    # Python dependencies
│   └── .env               # API keys (create from .env.example)
├── .gitignore             # Git ignore rules
├── .env.example           # Environment template
└── README.md              # This file
```
