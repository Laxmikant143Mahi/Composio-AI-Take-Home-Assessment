from typing import List, Optional, Literal
from pydantic import BaseModel, Field

# Constants for strict validation
AUTH_METHOD_TYPES = Literal["OAuth2", "API Key", "Basic Auth", "Token", "Other"]
DEV_ACCESS_TYPES = Literal["Self Serve", "Gated"]
API_COVERAGE_TYPES = Literal["Small", "Medium", "Broad"]
SUPPORT_STATUS_TYPES = Literal["Supported", "Unsupported", "Uncertain"]

class SaaSResearchModel(BaseModel):
    """Data structure representing raw SaaS API research findings."""
    app_name: str = Field(..., description="Name of the SaaS application")
    doc_url: str = Field(..., description="Official API documentation URL")
    dev_portal_url: str = Field(..., description="Developer portal or signup console URL")
    category: str = Field(..., description="SaaS category (e.g. Communication, Finance, Developer Tools, Sales & Marketing, etc.)")
    description: str = Field(..., description="One-line description of the SaaS application")
    auth_method: AUTH_METHOD_TYPES = Field(..., description="Primary authentication method")
    dev_access: DEV_ACCESS_TYPES = Field(..., description="Developer portal accessibility model")
    api_type: List[str] = Field(..., description="Types of APIs provided (e.g., REST, GraphQL, Webhooks, SDK)")
    api_coverage: API_COVERAGE_TYPES = Field(..., description="Estimated size/depth of API endpoints")
    mcp_server_exists: bool = Field(..., description="Whether an MCP server currently exists for this tool")
    composio_ready: bool = Field(..., description="Can Composio build a working toolkit today?")
    blocker: Optional[str] = Field(None, description="The primary blocker preventing instant integration, if composio_ready is False")
    evidence_urls: List[str] = Field(..., description="URLs of documentation pages used as core evidence")
    initial_confidence: float = Field(default=0.8, description="Initial research agent confidence estimation (0.0 to 1.0)")

class EvidenceValidation(BaseModel):
    """Validation status details for an individual evidence URL."""
    url: str = Field(..., description="The checked evidence URL")
    status_code: int = Field(..., description="HTTP response status code (e.g. 200, 404)")
    is_valid: bool = Field(..., description="Whether the URL is reachable (HTTP 2xx/3xx)")
    support_status: SUPPORT_STATUS_TYPES = Field(..., description="Does the URL content back up the research findings?")
    reasoning: str = Field(..., description="Short explanation of findings comparison")

class SaaSVerifiedModel(BaseModel):
    """Data structure representing verified research findings with confidence scores."""
    app_name: str = Field(..., description="Name of the SaaS application")
    research_data: SaaSResearchModel = Field(..., description="The raw researched data")
    evidence_validation: List[EvidenceValidation] = Field(default_factory=list, description="Validation details per evidence URL")
    final_confidence: float = Field(..., description="Calculated deterministic confidence score")
    needs_human_review: bool = Field(..., description="True if final_confidence < 0.75, routing to review queue")
    verification_notes: str = Field(..., description="Summarized explanation of verification checks")
