import streamlit as st
import re, time, math, requests, pandas as pd
from urllib.parse import quote_plus
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Configuration
SERPAPI_KEY = os.getenv("SERPAPI_KEY", "")
UNPAYWALL_EMAIL = os.getenv("UNPAYWALL_EMAIL", "you@example.com")
CURRENT_YEAR = int(os.getenv("CURRENT_YEAR", "2025"))

# Page config
st.set_page_config(
    page_title="Scholar Pulse Metrics",
    page_icon="📊",
    layout="wide"
)

# DOI regex pattern
DOI_RE = re.compile(r'10\.\d{4,9}/\S+', re.IGNORECASE)

# ========== API FUNCTIONS ==========

def serpapi_fetch_author(author_id, api_key):
    """Fetch author profile from SerpAPI"""
    url = f"https://serpapi.com/search.json?engine=google_scholar_author&author_id={author_id}&api_key={api_key}"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return r.json()

def extract_doi_from_serp_item(item):
    """Extract DOI from SerpAPI item"""
    ext = item.get("external_ids") or {}
    doi = ext.get("DOI") or ext.get("doi")
    if doi:
        return doi
    
    for k in ("inline_links", "links", "source", "publication_info", "publication"):
        val = item.get(k)
        if isinstance(val, dict):
            for v in val.values():
                if isinstance(v, str):
                    m = DOI_RE.search(v)
                    if m: return m.group(0)
        elif isinstance(val, list):
            for v in val:
                if isinstance(v, str):
                    m = DOI_RE.search(v)
                    if m: return m.group(0)
                elif isinstance(v, dict):
                    for s in v.values():
                        if isinstance(s, str):
                            m = DOI_RE.search(s)
                            if m: return m.group(0)
    return None

def fetch_crossref_by_doi(doi):
    """Fetch metadata from Crossref by DOI"""
    try:
        url = f"https://api.crossref.org/works/{quote_plus(doi)}"
        r = requests.get(url, headers={"User-Agent": "RIM-Collector/1.0"}, timeout=20)
        if r.status_code == 200:
            return r.json().get("message", {})
    except Exception:
        pass
    return {}

def fetch_crossref_by_title(title):
    """Fetch metadata from Crossref by title"""
    try:
        url = f"https://api.crossref.org/works?query.title={quote_plus(title)}&rows=1"
        r = requests.get(url, headers={"User-Agent": "RIM-Collector/1.0"}, timeout=20)
        r.raise_for_status()
        items = r.json().get("message", {}).get("items", [])
        return items[0] if items else {}
    except Exception:
        return {}

def parse_crossref_authors_and_affiliations(cr_item):
    """Parse author count and affiliations from Crossref data"""
    authors = cr_item.get("author", []) or []
    num_authors = len(authors)
    aff_names = []
    authors_with_aff = 0
    
    for a in authors:
        affs = a.get("affiliation", []) or []
        if affs:
            authors_with_aff += 1
            for aff in affs:
                if isinstance(aff, dict):
                    name = aff.get("name", "").strip()
                else:
                    name = str(aff).strip()
                if name:
                    aff_names.append(name)
    
    affs_unique = list(dict.fromkeys([a for a in aff_names if a]))
    return num_authors, authors_with_aff, "; ".join(affs_unique)

def fetch_semanticscholar_by_doi(doi):
    """Get citation data from Semantic Scholar by DOI"""
    try:
        url = f"https://api.semanticscholar.org/graph/v1/paper/DOI:{quote_plus(doi)}?fields=citationCount,year,isRetracted"
        r = requests.get(url, timeout=15)
        if r.status_code == 200:
            j = r.json()
            return int(j.get("citationCount", 0) or 0), j.get("year"), bool(j.get("isRetracted", False))
    except Exception:
        pass
    return 0, None, False

def fetch_semanticscholar_by_title(title):
    """Get citation data from Semantic Scholar by title"""
    try:
        url = f"https://api.semanticscholar.org/graph/v1/paper/search?query={quote_plus(title)}&limit=1&fields=title,citationCount,year,externalIds,isRetracted"
        r = requests.get(url, timeout=15)
        if r.status_code == 200:
            data = r.json().get("data", [])
            if data:
                item = data[0]
                return int(item.get("citationCount", 0) or 0), item.get("year"), bool(item.get("isRetracted", False)), item.get("externalIds", {})
    except Exception:
        pass
    return 0, None, False, {}

def fetch_unpaywall(doi, email):
    """Check if paper is Open Access via Unpaywall"""
    if not doi: return False
    try:
        url = f"https://api.unpaywall.org/v2/{doi}?email={quote_plus(email)}"
        r = requests.get(url, timeout=15)
        if r.status_code == 200:
            return bool(r.json().get("is_oa", False))
    except Exception:
        pass
    return False

def compute_cpy(citations, year):
    """Calculate Citations Per Year"""
    if not year or citations is None: return 0.0
    try:
        yrs = max(1, CURRENT_YEAR - int(year) + 1)
        return float(citations) / yrs
    except Exception:
        return 0.0

def compute_rim_with_logC(cpy, max_cpy, J=0.5, D=0.0, R=1.0, F=0.0, O=0.0, P=0.0):
    """Calculate Research Integrity Measure with log normalization"""
    if max_cpy and max_cpy > 0:
        C = math.log1p(cpy) / math.log1p(max_cpy)
    else:
        C = 0.0
    
    weights = {'C': 0.25, 'J': 0.20, 'D': 0.15, 'R': 0.20, 'F': 0.10, 'O': 0.05, 'P': 0.05}
    val = weights['C']*C + weights['J']*J + weights['D']*D + weights['R']*R + weights['F']*F + weights['O']*O + weights['P']*P
    return round(val * 100, 2)

def get_rim_color(rim_score):
    """Get color based on RIM score"""
    if rim_score >= 80:
        return "green"
    elif rim_score >= 60:
        return "blue"
    elif rim_score >= 40:
        return "orange"
    else:
        return "red"

def get_rim_badge(rim_score):
    """Get badge text based on RIM score"""
    if rim_score >= 80:
        return "Excellent"
    elif rim_score >= 60:
        return "Good"
    elif rim_score >= 40:
        return "Fair"
    else:
        return "Poor"

# ========== MAIN APP ==========

st.title("📊 Scholar Pulse Metrics")
st.markdown("### Research Integrity Measure (RIM) Analysis")

# Sidebar for configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    
    if not SERPAPI_KEY:
        st.error("⚠️ SERPAPI_KEY not found in .env file!")
        st.info("Get your key at: https://serpapi.com/")
    else:
        st.success("✅ API Key loaded")
    
    st.markdown("---")
    st.markdown("**About RIM Score:**")
    st.markdown("""
    - **80-100**: Excellent
    - **60-79**: Good
    - **40-59**: Fair
    - **0-39**: Poor
    """)

# Main input
scholar_id = st.text_input(
    "Enter Google Scholar ID",
    placeholder="e.g., tPeUsekAAAAJ",
    help="Find this in the Google Scholar profile URL"
)

analyze_button = st.button("🔍 Analyze Scholar", type="primary", use_container_width=True)

if analyze_button:
    if not scholar_id:
        st.error("Please enter a Scholar ID")
    elif not SERPAPI_KEY:
        st.error("Please configure SERPAPI_KEY in your .env file")
    else:
        with st.spinner("Fetching scholar profile..."):
            try:
                # Fetch profile
                data = serpapi_fetch_author(scholar_id, SERPAPI_KEY)
                scholar_name = data.get("author", {}).get("name", "") or ""
                serp_articles = data.get("articles", [])[:10]
                
                if not serp_articles:
                    st.warning("No publications found for this scholar ID")
                    st.stop()
                
                st.success(f"Found {len(serp_articles)} publications for **{scholar_name}**")
                
                # Progress bar
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                rows = []
                total = len(serp_articles)
                
                for idx, art in enumerate(serp_articles, start=1):
                    status_text.text(f"Processing paper {idx}/{total}...")
                    progress_bar.progress(idx / total)
                    
                    title_serp = art.get("title", "").strip()
                    
                    # Get cited_by from SerpAPI
                    cited_by_val = 0
                    try:
                        cb = art.get("cited_by")
                        if isinstance(cb, dict):
                            cited_by_val = int(cb.get("value", 0) or 0)
                        elif isinstance(cb, int):
                            cited_by_val = cb
                    except Exception:
                        cited_by_val = 0
                    
                    # Extract DOI
                    doi = extract_doi_from_serp_item(art)
                    
                    # Get Crossref metadata
                    cr = {}
                    if doi:
                        cr = fetch_crossref_by_doi(doi)
                    if not cr:
                        cr = fetch_crossref_by_title(title_serp)
                    
                    # Parse fields
                    title_cr = (cr.get("title", [""])[0]) if cr.get("title") else title_serp
                    journal = (cr.get("container-title", [""])[0]) if cr.get("container-title") else art.get("publication", {}).get("name") or art.get("source") or ""
                    volume = cr.get("volume", "") or ""
                    issue = cr.get("issue", "") or ""
                    
                    # Year
                    year = None
                    try:
                        year = cr.get('issued', {}).get('date-parts', [[None]])[0][0] or cr.get('published-print', {}).get('date-parts', [[None]])[0][0]
                    except Exception:
                        year = None
                    if not year:
                        year = art.get("year") or art.get("publication", {}).get("year")
                    
                    # Authors & affiliations
                    num_authors, authors_with_aff, affs_str = parse_crossref_authors_and_affiliations(cr) if cr else (0, 0, "")
                    if not num_authors:
                        serp_authors = art.get("authors") or art.get("authors_parsed") or []
                        if isinstance(serp_authors, list):
                            num_authors = len(serp_authors)
                    
                    # Funder info
                    funder_info = cr.get("funder", []) if cr else []
                    funder_flag = bool(funder_info)
                    
                    # DOI final
                    doi_final = (cr.get("DOI") or doi or "").strip()
                    
                    # Citations
                    citations = 0
                    is_retracted = False
                    if doi_final:
                        citations, sem_year, is_retracted = fetch_semanticscholar_by_doi(doi_final)
                    if (not doi_final) or (citations == 0 and not is_retracted):
                        sc_cit, sc_year, sc_retracted, sc_ext = fetch_semanticscholar_by_title(title_serp)
                        if sc_cit:
                            citations = sc_cit
                            if not doi_final:
                                doi_final = sc_ext.get("DOI") or sc_ext.get("doi") or doi_final
                            is_retracted = is_retracted or sc_retracted
                    if not citations:
                        citations = cited_by_val or 0
                    
                    # Open Access
                    is_oa = fetch_unpaywall(doi_final, UNPAYWALL_EMAIL) if doi_final else False
                    
                    # Author affiliation completeness
                    O_prop = (authors_with_aff / num_authors) if (num_authors and authors_with_aff is not None) else 0.0
                    
                    # Compile row
                    row = {
                        "Scholar Name": scholar_name,
                        "Title": title_cr,
                        "Journal/Conference": journal,
                        "Volume": volume,
                        "Issue": issue,
                        "Year": int(year) if year else None,
                        "Num_Authors": int(num_authors) if num_authors is not None else 0,
                        "Affiliations": affs_str or "N/A",
                        "DOI": doi_final or "",
                        "Citations": int(citations or 0),
                        "CPY": round(compute_cpy(citations or 0, year or None), 3),
                        "is_OA": bool(is_oa),
                        "Funder_present": funder_flag,
                        "Author_affil_completeness": round(O_prop, 3),
                        "Is_Retracted": bool(is_retracted)
                    }
                    rows.append(row)
                    time.sleep(1.0)  # Be polite to APIs
                
                # Build DataFrame
                df = pd.DataFrame(rows)
                max_cpy = df['CPY'].max() if not df['CPY'].isnull().all() else 0.0
                
                # Compute RIM
                df['RIM'] = df.apply(lambda r: compute_rim_with_logC(
                    cpy=r['CPY'],
                    max_cpy=max_cpy,
                    J=0.5,
                    D=float(r['is_OA']),
                    R=0.0 if r['Is_Retracted'] else 1.0,
                    F=float(r['Funder_present']),
                    O=float(r['Author_affil_completeness']),
                    P=0.0
                ), axis=1)
                
                # Add Risk Factor
                df['Risk_Factor'] = 1 - (df['RIM'] / 100)
                df['Risk_Factor'] = df['Risk_Factor'].clip(0, 1)
                
                progress_bar.empty()
                status_text.empty()
                
                # Display results
                st.markdown("---")
                st.header(f"📈 Results for {scholar_name}")
                
                # Summary metrics
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total Papers", len(df))
                with col2:
                    st.metric("Avg RIM Score", f"{df['RIM'].mean():.1f}")
                with col3:
                    st.metric("Total Citations", int(df['Citations'].sum()))
                with col4:
                    st.metric("Open Access", f"{(df['is_OA'].sum() / len(df) * 100):.0f}%")
                
                st.markdown("---")
                
                # Display each paper
                for idx, row in df.iterrows():
                    rim_score = row['RIM']
                    rim_color = get_rim_color(rim_score)
                    rim_badge = get_rim_badge(rim_score)
                    
                    with st.expander(f"**{idx+1}. {row['Title'][:80]}...**", expanded=(idx < 3)):
                        col1, col2 = st.columns([3, 1])
                        
                        with col1:
                            st.markdown(f"**Journal/Conference:** {row['Journal/Conference']}")
                            st.markdown(f"**Year:** {row['Year']} | **Citations:** {row['Citations']} | **CPY:** {row['CPY']:.2f}")
                            st.markdown(f"**Authors:** {row['Num_Authors']} | **DOI:** {row['DOI'] or 'N/A'}")
                            if row['Is_Retracted']:
                                st.error("⚠️ **RETRACTED**")
                            if row['is_OA']:
                                st.success("🔓 Open Access")
                        
                        with col2:
                            st.markdown(f"### RIM Score")
                            st.markdown(f"<h1 style='text-align: center; color: {rim_color};'>{rim_score:.1f}</h1>", unsafe_allow_html=True)
                            st.markdown(f"<p style='text-align: center;'><strong>{rim_badge}</strong></p>", unsafe_allow_html=True)
                
                # Download button
                st.markdown("---")
                
                # Convert to Excel
                from io import BytesIO
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False, sheet_name='Scholar Analysis')
                output.seek(0)
                
                st.download_button(
                    label="📥 Download Results (Excel)",
                    data=output,
                    file_name=f"{scholar_name.replace(' ', '_')}_RIM_analysis.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                
            except requests.exceptions.HTTPError as e:
                st.error(f"API Error: {e}")
                st.info("Check your SERPAPI_KEY or Scholar ID")
            except Exception as e:
                st.error(f"Error: {str(e)}")
                st.exception(e)
