def get_dark_theme_css() -> str:
    return """<style>
    /* Dark Theme Colors */
    :root {
        --bg-primary: #0f172a;
        --bg-secondary: #1e293b;
        --bg-card: #1e293b;
        --text-primary: #f1f5f9;
        --text-secondary: #94a3b8;
        --accent-purple: #8b5cf6;
        --accent-blue: #3b82f6;
        --border-color: #334155;
    }

    /* Global Dark Theme */
    .stApp {
        background-color: var(--bg-primary);
    }

    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background-color: var(--bg-secondary);
        border-right: 1px solid var(--border-color);
    }

    [data-testid="stSidebar"] .stRadio > label {
        color: var(--text-primary) !important;
    }

    [data-testid="stSidebar"] .stRadio > div {
        color: var(--text-secondary);
    }

    /* Main Header */
    .main-header {
        font-size: 2rem;
        font-weight: 600;
        color: var(--text-primary);
        margin-bottom: 1.5rem;
        letter-spacing: -0.5px;
    }

    /* Modern Cards */
    .stMetric {
        background-color: var(--bg-card);
        border: 1px solid var(--border-color);
        border-radius: 12px;
        padding: 1.25rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    }

    .stMetric > div {
        color: var(--text-secondary);
        font-size: 0.875rem;
        font-weight: 500;
    }

    .stMetric > div[data-testid="stMetricValue"] {
        color: var(--text-primary);
        font-size: 1.75rem;
        font-weight: 700;
    }

    /* Metric Cards */
    .metric-card {
        background-color: var(--bg-card);
        border: 1px solid var(--border-color);
        border-radius: 12px;
        padding: 1.5rem;
        color: var(--text-primary);
        margin: 0.75rem 0;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        transition: transform 0.2s, box-shadow 0.2s;
    }

    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.2);
    }

    .metric-value {
        font-size: 1.75rem;
        font-weight: 700;
        color: var(--text-primary);
    }

    .metric-label {
        font-size: 0.875rem;
        color: var(--text-secondary);
        font-weight: 500;
    }

    /* Buttons */
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        height: 2.75rem;
        font-weight: 600;
        background-color: var(--accent-purple);
        color: white;
        border: none;
        transition: all 0.2s;
    }

    .stButton>button:hover {
        background-color: #7c3aed;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(139, 92, 246, 0.4);
    }

    .stButton>button:active {
        transform: translateY(0);
    }

    /* Secondary Button */
    .secondary-button > button {
        background-color: transparent;
        border: 1px solid var(--border-color);
        color: var(--text-primary);
    }

    .secondary-button > button:hover {
        background-color: rgba(255, 255, 255, 0.05);
    }

    /* Tables */
    .stDataFrame {
        background-color: var(--bg-card);
        border: 1px solid var(--border-color);
        border-radius: 12px;
        overflow: hidden;
        max-width: 100%;
    }

    .stDataFrame > div {
        overflow-x: auto !important;
    }

    .stDataFrame table {
        width: 100%;
        table-layout: auto;
    }

    .stDataFrame thead th {
        background-color: var(--bg-secondary);
        color: var(--text-primary);
        font-weight: 600;
        border-bottom: 1px solid var(--border-color);
        white-space: nowrap;
        padding: 0.75rem 1rem;
    }

    .stDataFrame tbody td {
        color: var(--text-secondary);
        border-bottom: 1px solid var(--border-color);
        padding: 0.5rem 1rem;
        white-space: nowrap;
    }

    /* Main content container */
    .main .block-container {
        max-width: 100%;
        padding: 2rem;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        background-color: var(--bg-secondary);
        border-radius: 8px;
        padding: 0.25rem;
    }

    .stTabs [data-baseweb="tab"] {
        color: var(--text-secondary);
        border-radius: 6px;
    }

    .stTabs [data-baseweb="tab-highlight"] {
        background-color: var(--accent-purple);
        border-radius: 6px;
    }

    /* Select Box */
    .stSelectbox > div > div {
        background-color: var(--bg-secondary);
        border: 1px solid var(--border-color);
        color: var(--text-primary);
        border-radius: 8px;
    }

    /* Text Input */
    .stTextInput > div > div > input {
        background-color: var(--bg-secondary);
        border: 1px solid var(--border-color);
        color: var(--text-primary);
        border-radius: 8px;
    }

    /* Download Button */
    .stDownloadButton > button {
        background-color: transparent;
        border: 1px solid var(--accent-purple);
        color: var(--accent-purple);
    }

    .stDownloadButton > button:hover {
        background-color: rgba(139, 92, 246, 0.1);
    }

    /* Status Indicators */
    .status-online {
        color: #10b981;
        font-weight: 600;
    }

    .status-offline {
        color: #ef4444;
        font-weight: 600;
    }

    /* Chat Messages */
    .chat-message {
        padding: 1rem;
        border-radius: 12px;
        margin: 0.75rem 0;
        font-size: 14px;
        line-height: 1.5;
    }

    .chat-user {
        background-color: rgba(59, 130, 246, 0.15);
        margin-left: 15%;
        color: var(--text-primary);
        border: 1px solid rgba(59, 130, 246, 0.3);
    }

    .chat-bot {
        background-color: rgba(139, 92, 246, 0.15);
        margin-right: 15%;
        color: var(--text-primary);
        border: 1px solid rgba(139, 92, 246, 0.3);
    }

    .chat-bot pre {
        background-color: var(--bg-secondary);
        padding: 0.75rem;
        border-radius: 6px;
        overflow-x: auto;
        font-size: 12px;
        border: 1px solid var(--border-color);
    }

    /* Info Cards */
    .info-card {
        background-color: var(--bg-card);
        border: 1px solid var(--border-color);
        border-radius: 12px;
        padding: 1.25rem;
        margin: 0.75rem 0;
    }

    .info-card h4 {
        color: var(--text-primary);
        font-weight: 600;
        margin-bottom: 0.75rem;
    }

    .info-card p {
        color: var(--text-secondary);
        font-size: 0.875rem;
    }

    /* Section Headers */
    h3 {
        color: var(--text-primary);
        font-weight: 600;
        font-size: 1.25rem;
        margin-top: 1.5rem;
        margin-bottom: 1rem;
    }

    /* Expander */
    .stExpander {
        background-color: var(--bg-card);
        border: 1px solid var(--border-color);
        border-radius: 12px;
        overflow: hidden;
    }

    /* Success/Error Messages */
    .stSuccess {
        background-color: rgba(16, 185, 129, 0.15);
        border: 1px solid rgba(16, 185, 129, 0.3);
        color: #34d399;
        border-radius: 8px;
    }

    .stError {
        background-color: rgba(239, 68, 68, 0.15);
        border: 1px solid rgba(239, 68, 68, 0.3);
        color: #f87171;
        border-radius: 8px;
    }

    .stInfo {
        background-color: rgba(59, 130, 246, 0.15);
        border: 1px solid rgba(59, 130, 246, 0.3);
        color: #60a5fa;
        border-radius: 8px;
    }
</style>"""
