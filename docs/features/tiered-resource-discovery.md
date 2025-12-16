# Tiered Resource Discovery System

## Overview

The Tiered Resource Discovery System categorizes educational resources (textbooks, curricula, guides, videos) into three tiers based on their source of authority:

| Tier | Description | Example Sources |
|------|-------------|-----------------|
| **Official** | Published or endorsed by the standards authority itself | TEA Instructional Materials, College Board AP Classroom |
| **Recommended** | Recommended by professional organizations or experts | NCTM resources, EdReports green-rated curricula |
| **Commonly Used** | Found on school district/school websites | Houston ISD curriculum, Dallas ISD adopted textbooks |

This approach ensures teachers can distinguish between authoritative resources and those discovered through other means.

## Key Design Decision

**Google Books is for metadata enrichment only, not resource discovery.**

- Official resources come from authority websites (TEA, FLDOE, College Board)
- Recommended resources come from professional organizations (NCTM, NCTE, NSTA)
- Commonly used resources come from school district websites
- Google Books API is used only to add ISBNs, cover images, and descriptions to already-discovered resources

## Architecture

### Model: `AuthorityProgramMedia`

```python
RECOMMENDATION_TIERS = [
    ("official", "Official"),
    ("recommended", "Recommended"),
    ("commonly_used", "Commonly Used"),
]

# New fields
recommendation_tier = CharField(choices=RECOMMENDATION_TIERS, default="commonly_used")
discovered_from_url = URLField(blank=True)  # Where the resource was found
recommending_organization = CharField(blank=True)  # Who recommended it
```

### Discovery Functions

Located in `core/services/resources/discovery.py`:

| Function | Purpose | Output Tier |
|----------|---------|-------------|
| `discover_from_authority_website()` | Scrapes authority resource pages | `official` |
| `discover_from_professional_org()` | Scrapes professional org pages | `recommended` |
| `discover_from_district_website()` | Scrapes district curriculum pages | `commonly_used` |
| `enrich_with_google_books()` | Adds metadata to existing resources | (preserves tier) |

### AI-Assisted Extraction

The `extract_resources_with_ai()` function uses Claude Haiku to parse web pages and extract structured resource information:

```python
ExtractedResource:
    title: str
    url: str
    author: str
    publisher: str
    description: str
    media_type: str  # book, curriculum, guide, etc.
    isbn: str
    confidence: float  # 0.0-1.0
```

Resources with confidence < 0.5 are filtered out for official/recommended tiers, < 0.4 for commonly used.

## Known Resource Pages

Pre-configured URLs for automated discovery:

### Authority Pages (`AUTHORITY_RESOURCE_PAGES`)
- STATE_TX: TEA Instructional Materials, Texas Resource Review
- STATE_FL: FLDOE Instructional Materials
- STATE_CA: CDE Instructional Materials
- CCSS_ELA/MATH: Common Core website

### Professional Organizations (`PROFESSIONAL_ORG_PAGES`)
- Mathematics: NCTM
- ELA: NCTE, International Literacy Association
- Science: NSTA

### District Pages (`DISTRICT_CURRICULUM_PAGES`)
- Texas: Houston ISD, Dallas ISD, Austin ISD
- Florida: Miami-Dade, Broward County
- California: Los Angeles USD, San Diego USD

## UI Display

The resources panel in Standards Browse displays three collapsible sections:

```
Supporting Resources (12)
├── [Official] (3)                    [green header]
│   └── Published or endorsed by the standards authority
│       ├── TEA Instructional Materials
│       └── Texas Resource Review
├── [Recommended] (4)                 [blue header]
│   └── Recommended by professional organizations
│       ├── Illustrative Mathematics (EdReports Green Rating)
│       └── ReadWorks (EdReports)
└── [Commonly Used] (5)               [gray header]
    └── Found on district and school websites
        ├── Khan Academy - Math (Used by Houston ISD)
        └── CommonLit
```

Each resource card shows:
- Cover image (if available)
- Title (linked to source URL)
- Author and media type badges
- Endorsement notes or recommending organization

## API Response

The `standards_api_results` endpoint returns resources with tier information:

```json
{
  "resources": [
    {
      "id": 123,
      "title": "TEA Instructional Materials",
      "recommendation_tier": "official",
      "recommendation_tier_display": "Official",
      "endorsement_notes": "Official TEA adopted materials",
      "recommending_organization": "Texas Education Agency",
      "media_type": "guide",
      "platform": "authority",
      "source_url": "https://tea.texas.gov/...",
      "cover_image_url": "..."
    }
  ]
}
```

Resources are ordered by tier priority: official → recommended → commonly_used.

## Background Job Integration

The resource sync job (`sync_authority_resources`) uses these discovery functions:

1. For each program under an authority:
   - Check if a resource provider is registered
   - Call `discover_resources()` on the provider
   - Create/update `AuthorityProgramMedia` records
   - Link to objectives where possible
2. Optionally enrich with Google Books metadata

## Files Modified

| File | Changes |
|------|---------|
| `core/models.py` | Added `recommendation_tier`, `discovered_from_url`, `recommending_organization` fields |
| `core/services/resources/base.py` | Updated `ResourceData` dataclass with tier fields |
| `core/services/resources/discovery.py` | Added AI discovery functions, updated curated resources |
| `core/services/resources/__init__.py` | Exported new functions |
| `core/views.py` | Updated API to return tier information |
| `core/templates/core/teacher/standards_browse.html` | Three-section resources panel UI |

## Migration

Migration `0019_add_recommendation_tier_fields.py` adds:
- `recommendation_tier` field with default "commonly_used"
- `discovered_from_url` field
- `recommending_organization` field
- Index on `(authority_program, recommendation_tier)`

## Usage Example

```python
from core.services.resources import (
    discover_from_authority_website,
    enrich_resources_batch,
    AUTHORITY_RESOURCE_PAGES,
)

# Discover official resources from TEA
tea_info = AUTHORITY_RESOURCE_PAGES["STATE_TX"]
resources = discover_from_authority_website(
    authority_url=tea_info["official_pages"][0],
    authority_name=tea_info["name"],
    subject="Mathematics",
    grade_level="Grade 6",
)

# Enrich with Google Books metadata
enriched = enrich_resources_batch(resources)

# All resources are marked as "official" tier
for r in enriched:
    print(f"{r.title} - {r.recommendation_tier}")
```

## Configuration

Requires `ANTHROPIC_API_KEY` in Django settings for AI-assisted extraction. Without it, AI extraction is skipped with a warning.
