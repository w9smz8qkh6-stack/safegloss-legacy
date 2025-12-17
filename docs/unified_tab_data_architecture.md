# Unified External Data Source Architecture

This document describes the redesigned architecture for fetching and displaying tab data for standards courses.

## Overview

The unified architecture provides:
1. **Database-driven tab configurations** - No more hardcoded JS configs
2. **Unified OpenRouter AI extraction** - Single entry point for all AI-powered data fetching
3. **Tab-specific fetch methods** - Each tab type has its own data fetching strategy
4. **Easy provider addition** - Add new providers without code changes

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (JS)                            │
│  fetchTabConfigFromAPI() ──► fetchUnifiedTabData()              │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      API Endpoints                              │
│  /api/tab-config/           /api/document/<id>/tab/<tab_id>/    │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    UnifiedAIFetcher                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ ai_extract   │  │ objectives   │  │ resources    │          │
│  │ (OpenRouter) │  │ (DB query)   │  │ (DB query)   │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Database                                   │
│  ProviderTabConfig ──► TabDataCache ──► StandardsDocument       │
└─────────────────────────────────────────────────────────────────┘
```

## Database Models

### ProviderTabConfig

Stores tab configuration for each authority/program.

| Field | Description |
|-------|-------------|
| `authority` | FK to StandardsAuthority (for authority-wide configs) |
| `program` | FK to AuthorityProgram (for program-specific overrides) |
| `tab_id` | Tab identifier (e.g., 'overview', 'syllabus') |
| `label` | Display label |
| `icon` | Bootstrap icon class |
| `sort_order` | Tab ordering |
| `fetch_method` | How to fetch data: `none`, `objectives`, `resources`, `ai_extract`, `custom` |
| `ai_extraction_prompt` | Custom prompt for AI extraction |
| `custom_handler` | Dotted path to custom handler function |

### TabDataCache

Caches fetched tab data per document.

| Field | Description |
|-------|-------------|
| `document` | FK to StandardsDocument |
| `tab_id` | Tab identifier |
| `data` | Cached JSON data |
| `fetch_status` | `pending`, `fetching`, `success`, `error` |
| `fetched_at` | Timestamp |
| `ai_model_used` | Model used for AI extraction |
| `tokens_used` | Tokens consumed |

## API Endpoints

### GET `/teacher/standards/api/tab-config/`

Get tab configuration for an authority/program.

**Query params:**
- `authority_code` (required): Authority code (e.g., `CAMBRIDGE`)
- `program_code` (optional): Program code for overrides

**Response:**
```json
{
  "tabs": [
    {"id": "overview", "label": "Overview", "icon": "bi-info-circle", "fetch_method": "none"},
    {"id": "syllabus", "label": "Syllabus", "icon": "bi-file-text", "fetch_method": "ai_extract"}
  ],
  "using_defaults": false
}
```

### GET `/teacher/standards/api/document/<document_id>/tab/<tab_id>/`

Fetch data for a specific tab.

**Query params:**
- `force_refresh` (optional): Set to `1` to bypass cache

**Response:**
```json
{
  "data": { /* tab-specific data */ },
  "cached": true,
  "fetched_at": "2025-12-17T12:00:00Z",
  "fetch_method": "ai_extract"
}
```

## Fetch Methods

| Method | Description | Data Source |
|--------|-------------|-------------|
| `none` | Static content only | Document fields |
| `objectives` | Fetch objectives tree | ObjectiveNode table |
| `resources` | Fetch resources | AuthorityProgramMedia table |
| `ai_extract` | AI extraction via OpenRouter | OpenRouter API |
| `custom` | Custom handler function | Specified module.function |

## Adding a New Provider

No code changes required! Just add database entries:

```python
from core.models import StandardsAuthority, ProviderTabConfig

# 1. Create the authority
authority = StandardsAuthority.objects.create(
    code="NEW_PROVIDER",
    name="New Provider Name",
    is_active=True
)

# 2. Add tab configurations
tabs = [
    {"tab_id": "overview", "label": "Overview", "icon": "bi-info-circle", "fetch_method": "none"},
    {"tab_id": "curriculum", "label": "Curriculum", "icon": "bi-book", "fetch_method": "ai_extract",
     "ai_extraction_prompt": "Extract curriculum structure for {course_name}..."},
    {"tab_id": "objectives", "label": "Learning Objectives", "icon": "bi-list-check", "fetch_method": "objectives"},
    {"tab_id": "resources", "label": "Resources", "icon": "bi-collection", "fetch_method": "resources"},
]

for i, tab in enumerate(tabs):
    ProviderTabConfig.objects.create(
        authority=authority,
        tab_id=tab["tab_id"],
        label=tab["label"],
        icon=tab["icon"],
        fetch_method=tab["fetch_method"],
        ai_extraction_prompt=tab.get("ai_extraction_prompt", ""),
        sort_order=i,
        is_active=True
    )
```

## Default AI Extraction Prompts

The `UnifiedAIFetcher` includes default prompts for common tab types:

- **syllabus**: Extracts aims, assessment objectives, content outline, assessment structure
- **objectives**: Extracts hierarchical learning objectives with codes
- **resources**: Finds textbooks, guides, past papers, digital resources
- **examinations**: Extracts exam format, papers, grading, specimen papers
- **overview**: Provides course summary, key features, prerequisites

Custom prompts can override these via `ai_extraction_prompt` field.

## Files

| File | Purpose |
|------|---------|
| `core/models.py` | ProviderTabConfig, TabDataCache models |
| `core/services/external/ai_fetcher.py` | UnifiedAIFetcher class |
| `core/views.py` | API endpoints |
| `core/urls.py` | URL routing |
| `core/management/commands/seed_default_tab_configs.py` | Seeder command |

## Management Commands

### Seed Default Tab Configs

```bash
# Dry run
python manage.py seed_default_tab_configs --dry-run

# Seed all authorities
python manage.py seed_default_tab_configs

# Seed specific authority
python manage.py seed_default_tab_configs --authority CAMBRIDGE

# Force update existing
python manage.py seed_default_tab_configs --force
```

## Current State

- **66 tab configs** seeded across 10+ authorities
- Fallback to hardcoded JS configs for backwards compatibility
- Cache invalidation via `TabDataCache.invalidate()` or `force_refresh=1`

## Future Enhancements

1. **Admin UI** for managing tab configs without code
2. **Async job processing** for AI extraction (currently synchronous)
3. **Rate limiting** for OpenRouter API calls
4. **Webhook** for cache invalidation when source documents change
