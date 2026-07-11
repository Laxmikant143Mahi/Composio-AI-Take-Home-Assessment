# SaaS Research Platform (Composio Product Ops Assignment)

An AI-powered SaaS Research and Verification Platform that automates the analysis of developer portals across 100 applications. It assesses API types, authentication schemes, developer onboarding accessibility, and toolkit feasibility for Composio, providing a verified dynamic dashboard to guide integration roadmaps.

---

## 1. Project Overview

Composio develops tools and integration frameworks that allow AI agents to interact with third-party software. Identifying which applications are ready to integrate versus which are gated or require custom partnerships is a core product operations challenge. 

This platform automates that assessment. Given a list of 100 SaaS applications, it discovers documentation links, scrapes relevant developer pages, uses LLMs for structured metadata extraction, verifies findings against live network pings, and cross-checks content using a secondary LLM verification model. It outputs a premium static HTML dashboard presenting aggregated analytics, qualitative business insights, dynamic verification accuracy, and a searchable matrix of findings.

---

## 2. High-Level Design (HLD)

The platform is constructed as a decoupled, local-first hybrid data pipeline that automates the ingestion, crawling, analysis, and validation of developer documentation. 

### System Topology & Data Flow
The system processes applications through a sequential flow, utilizing a local cache layer to protect API limits while preserving the live crawling capability.

```mermaid
graph TD
    A[data/saas_input.csv] -->|1. Ingestion| B[run.py Pipeline CLI]
    B -->|2. Delegate Research| C[Research Agent]
    C -->|3a. Check Cache| D[(data/research_cache.json)]
    C -->|3b. Live Search Miss| E[Composio SDK / Tavily]
    C -->|3c. Parse Page text| F[OpenAI API gpt-4o-mini]
    
    B -->|4. Delegate Verification| G[Verification Agent]
    G -->|5a. URL Reachability check| H[Web Scraper Pings]
    G -->|5b. Semantic Audit check| F
    
    B -->|6. Compile Aggregations| I[Analytics Engine]
    I -->|Compare Ground Truth| J[data/manual_verification.json]
    
    B -->|7. Render templates| K[Report Generator]
    K -->|8. Generate Dashboard| L[output/report.html]
    K -->|9. Export Homepage| M[index.html at root]
```

---

## 3. Low-Level Design (LLD)

The platform splits the business logic into distinct layers to maintain strict modularity:

### Class Architecture & UML-style Schema
The primary classes are typed via Pydantic v2 to ensure schema compliance before any JSON writes occur.

```mermaid
classDiagram
    class ResearchAgent {
        +composio_client: Composio
        +composio_tools: list
        +composio_user_id: str
        +research_app(app_name: str) SaaSResearchModel
        -_execute_research(app_name: str) SaaSResearchModel
    }
    class VerificationAgent {
        +scraper: WebScraper
        +manual_truth: list
        +client: OpenAI
        +verify_findings(research_data: SaaSResearchModel) SaaSVerifiedModel
        -_llm_verify_evidence(research_data: SaaSResearchModel, url: str, text: str) tuple
    }
    class WebScraper {
        +session: Session
        +playwright_browser: Browser
        +search_documentation(app_name: str, query_type: str) list
        +fetch_page_content(url: str) str
        +ping_url(url: str) int
    }
    class AnalyticsEngine {
        +manual_truth: list
        +generate_analytics(items: list) dict
    }
    
    ResearchAgent --> WebScraper : Uses for fetches
    VerificationAgent --> WebScraper : Uses for pings
    VerificationAgent ..> SaaSResearchModel : Inspects
    VerificationAgent ..> SaaSVerifiedModel : Produces
```

### Module Breakdown
1.  **Ingestion & State Manager (`run.py`)**: Responsible for loading input CSV files, managing incremental checkpoints (saving progress after every application), and building final service engines.
2.  **Research Agent (`src/agents/research.py`)**:
    *   **Documentation Discovery Layer**: Invokes the **Composio SDK** to fetch Tavily Search tool metadata, resolving URL searches. If the SDK is not configured, it falls back to DuckDuckGo search.
    *   **JSON Schema Extraction**: Directs `gpt-4o-mini` using the OpenAI Structured Outputs parser to strictly enforce validation constraints on the `SaaSResearchModel` class.
3.  **Verification Agent (`src/agents/verification.py`)**:
    *   **Status Check Engine**: Directly triggers network pings against extracted target domains. 
    *   **Confidence Calculator**: Employs a deterministic heuristic formula (weighed between HTTP status codes and LLM evidence validations) to assess correctness.
    *   **Human Router**: Sets `needs_human_review = True` for any application falling below the `0.75` score threshold.
4.  **Low-Level Web Scraper (`src/scraper/web_scraper.py`)**:
    *   **Requests session**: Manages network connections, cookie storage, and user-agent rotation.
    *   **Playwright Engine**: A headless browser wrapper that launches in standard Chromium to render JavaScript-heavy Single Page Applications (SPAs) when requests return connection status codes `403` or Cloudflare locks.
5.  **Analytics Service (`src/services/analytics.py`)**:
    *   Aggregates auth mechanisms, category trends, onboarding accessibility distributions, and computes the dynamic verification accuracy score.
6.  **Report Compiler (`src/services/report_generator.py`)**:
    *   Uses Jinja2 to compile data models directly into a premium HTML5 webpage, injecting live Chart.js config data.

---

## 4. How It Works (Workflow)

```mermaid
sequenceDiagram
    autonumber
    actor CLI as run.py
    participant ResAgent as ResearchAgent
    participant Scraper as WebScraper
    participant OpenAI as OpenAI API (gpt-4o-mini)
    participant VerAgent as VerificationAgent
    participant Cache as data/research_cache.json

    CLI->>ResAgent: Research SaaS App
    ResAgent->>Cache: Lookup normalized app name
    alt Cache Hit
        Cache-->>ResAgent: Load cached findings
    else Cache Miss
        ResAgent->>Scraper: Search via Composio SDK (Tavily) & retrieve HTML
        Scraper-->>ResAgent: Clean HTML text and URLs
        ResAgent->>OpenAI: structured extraction query
        OpenAI-->>ResAgent: SaaSResearchModel JSON object
        ResAgent->>Cache: Save findings to file
    end
    ResAgent-->>CLI: Research Data
    
    CLI->>VerAgent: Verify findings
    VerAgent->>Scraper: Ping doc, portal, and evidence URLs
    Scraper-->>VerAgent: Response status codes & scraped page content
    VerAgent->>OpenAI: Request comparison (Scraped Text vs Findings)
    OpenAI-->>VerAgent: Classification (Supported/Unsupported/Uncertain) + Reasoning
    VerAgent->>VerAgent: Calculate deterministic confidence score
    VerAgent-->>CLI: SaaSVerifiedModel JSON object
```

---

## 5. Verification Strategy & Confidence Score

To ensure data reliability, the Verification Agent calculates a deterministic confidence score:

$$\text{Confidence Score} = (0.20 \times \text{Doc URL Valid}) + (0.20 \times \text{Dev Portal URL Valid}) + (0.45 \times \text{LLM Verification Status}) + (0.15 \times \text{Multi-Evidence URLs})$$

*   **Doc URL Valid (20%)**: `0.20` if the official documentation URL returns HTTP `2xx` or `3xx`.
*   **Dev Portal URL Valid (20%)**: `0.20` if the developer portal URL returns HTTP `2xx` or `3xx`.
*   **LLM Verification Status (45%)**:
    *   `0.45` if all checked evidence URLs return `Supported` when evaluated against scraped contents.
    *   `0.20` if any URL check returns `Uncertain` (and none `Unsupported`).
    *   `0.00` if any check returns `Unsupported`.
*   **Multiple Evidence URLs (15%)**: `0.15` if there are two or more distinct evidence URLs verifying findings.

*Note: These weights are heuristic and were chosen to prioritize evidence-backed verification over simple URL availability. They can be calibrated using historical validation data in a production environment.*

If the final confidence score falls below **`0.75`**, `needs_human_review` is set to `True`, routing the record to the **Human Review Queue**.

---

## 6. Technology Stack

*   **Core**: Python 3.13
*   **Data Models**: Pydantic v2
*   **Agent LLM**: OpenAI API (using Structured Outputs parsing on `gpt-4o-mini`)
*   **Scraping & Discovery**: DuckDuckGo Search API (`duckduckgo_search`), `requests` (with urllib3 adapters), `BeautifulSoup4`, and `Playwright` headless browser rendering.
*   **Analytics**: `pandas`
*   **HTML Dashboard Rendering**: Jinja2 templating, Chart.js (static CDN charts), and Vanilla CSS (Glassmorphism layout).

---

## 7. Installation & Setup

1.  Clone the repository and navigate to the project directory:
    ```bash
    cd capsicono
    ```
2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
3.  Configure environment variables:
    *   To run **live AI-First web research crawls**:
        ```bash
        # Command Prompt (Windows)
        set OPENAI_API_KEY=your-api-key-here
        
        # PowerShell (Windows)
        $env:OPENAI_API_KEY="your-api-key-here"
        ```
    *   To run **Development Mode (Cached)**:
        Simply omit setting `OPENAI_API_KEY`. The platform's agents automatically load pre-cached results from `data/research_cache.json` (falling back to manual ground-truth mappings if cache misses occur), bypassing live search engines and HTTP network requests to run instantly without requiring API keys.

---

## 8. How to Run

1.  **Seed Datasets**:
    The input dataset of 100 applications (`data/saas_input.csv`) and verification ground truths (`data/manual_verification.json`) are already pre-seeded and packaged directly in this repository. No extra setup is required to prepare the dataset.
2.  **Execute Platform Pipeline**:
    ```bash
    # Run the full pipeline for all 100 applications
    python run.py
    ```
    *   **Advanced CLI Flags**:
        *   `--nocache`: Bypass the cache database (`data/research_cache.json`) and force live crawlers to query web search indices.
        *   `--limit N`: Processes only the first `N` applications in the input CSV list. *Recommended for checking live LLM crawls on 3-5 applications without spending significant API credits.*
3.  **View Output Report**:
    Open `output/report.html` directly in any web browser to view the interactive dashboard.

---

## 9. Design Decisions & Trade-Offs

*   **Hybrid Development/Production Modes**: Running 100 live browser fetches and OpenAI API calls during a take-home assessment review is slow and costly. We built a zero-config local Development Mode (which executes when `OPENAI_API_KEY` is missing) that loads high-fidelity cached blueprints from our manual ground-truth databases instantly, while keeping the full live crawl extraction pathway (Production Mode) ready for active API keys.
*   **No Event Bus or MQ**: The platform uses a clean, sequential Python CLI pipeline instead of heavy message queues (like Kafka or RabbitMQ) to prioritize simplicity and keep the code easily explainable by an intern during interviews.
*   **Incremental Cache Checkpoint saving**: Rather than writing output files only at the end, the CLI saves intermediate findings after each application, allowing the process to resume seamlessly if aborted.

---

## 10. Key Limitations & Human Intervention boundaries

1.  **Portals Behind Logins**: Enterprise applications (like Salesforce, ADP, or Workday) restrict deep developer credential pages behind login walls. The Research Agent cannot bypass these, generating lower confidence metrics that route them to the human review queue.
2.  **JavaScript-Heavy SPAs**: Developer documentation sites that do not render static HTML structures fail requests checks, requiring CPU-heavy Playwright headless browser rendering.
3.  **Cloudflare/WAF Blocks**: Frequent search and scraping requests can trigger bot-protection blocks. While handled using retry adapters and exponential backoffs, a production environment requires proxy rotation pools.
