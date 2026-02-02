import json
import time
from openai import OpenAI
from config import Config
from utils.database import get_brand_assets, get_brand_by_id, get_audience_by_id


def get_openai_client():
    """Get OpenAI client."""
    if not Config.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY not configured")
    return OpenAI(api_key=Config.OPENAI_API_KEY)


def extract_relevant_assets_text(brand_id, asset_types=None, max_chars=10000):
    """Extract and concatenate text from relevant brand assets."""
    assets = get_brand_assets(brand_id)
    relevant_text = []

    for asset in assets:
        if asset_types is None or asset['asset_type'] in asset_types:
            if asset['extracted_text']:
                text = asset['extracted_text'][:max_chars // len(asset_types) if asset_types else max_chars // 3]
                relevant_text.append(f"[{asset['asset_type']} - {asset['file_name']}]:\n{text}")

    return "\n\n".join(relevant_text)


def generate_content(brand_id, asset_type, audience_id, custom_audience, additional_context, retries=3):
    """Generate content using OpenAI API."""
    brand = get_brand_by_id(brand_id)
    if not brand:
        return None, "Brand not found"

    # Get audience information
    audience_text = ""
    if audience_id:
        audience = get_audience_by_id(audience_id)
        if audience:
            audience_text = f"{audience['audience_name']}: {audience['audience_description']}"
    elif custom_audience:
        audience_text = custom_audience

    # Build context from brand assets
    brand_context = extract_relevant_assets_text(
        brand_id,
        ['Feature Description', 'GTM Strategy', 'Marketing Material', 'Pitch Deck'],
        max_chars=8000
    )

    tone_reference = extract_relevant_assets_text(
        brand_id,
        ['Marketing Material'],
        max_chars=4000
    )

    regulatory_context = extract_relevant_assets_text(
        brand_id,
        ['Regulatory'],
        max_chars=3000
    )

    # Build the system message for better context
    system_message = f"""You are an expert marketing content creator specializing in healthcare and medical technology marketing. You create compelling, on-brand content that adheres to regulatory guidelines.

Your task is to create {asset_type} content for {brand['brand_name']}.

BRAND OVERVIEW:
{brand['description']}

TONE & STYLE REFERENCE (match this style):
{tone_reference if tone_reference else "Professional, innovative, and trustworthy. Focus on clinical outcomes and efficiency gains."}

REGULATORY CONSIDERATIONS:
{regulatory_context if regulatory_context else "Ensure all claims are substantiated and avoid making diagnostic claims that would require FDA clearance. Focus on workflow improvements and efficiency gains rather than diagnostic accuracy claims."}"""

    # Build the user prompt
    user_prompt = f"""Create {asset_type} content for {brand['brand_name']} with the following specifications:

BRAND CONTEXT AND PRODUCT INFORMATION:
{brand_context if brand_context else "No specific brand assets uploaded yet. Create content based on general knowledge of digital pathology and AI-powered diagnostic solutions."}

TARGET AUDIENCE:
{audience_text if audience_text else "Healthcare professionals and pathology laboratory decision-makers"}

ADDITIONAL REQUIREMENTS:
{additional_context if additional_context else "None specified"}

Please create compelling, on-brand {asset_type} content that:
1. Matches the brand's established tone and messaging
2. Speaks directly to the target audience's needs and pain points
3. Incorporates key product features and value propositions
4. Adheres to regulatory guidelines for medical/healthcare marketing
5. Is formatted appropriately for a {asset_type}

Format Guidelines for {asset_type}:
{get_format_guidelines(asset_type)}

Generate the content now:"""

    # Call OpenAI API with retries
    client = get_openai_client()

    for attempt in range(retries):
        try:
            response = client.chat.completions.create(
                model=Config.OPENAI_MODEL,
                max_tokens=4096,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_prompt}
                ]
            )
            return response.choices[0].message.content, None
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
            else:
                return None, f"API error after {retries} attempts: {str(e)}"

    return None, "Unknown error"


def get_format_guidelines(asset_type):
    """Get formatting guidelines for different asset types."""
    guidelines = {
        'Brochure': """
- Include a compelling headline
- Use bullet points for key features/benefits
- Include sections: Overview, Key Features, Benefits, Call to Action
- Keep paragraphs short and scannable
- Include suggested image/visual placements marked as [IMAGE: description]""",

        'Postcard': """
- Very concise - front and back copy
- Strong headline (5-8 words)
- 2-3 key benefit points
- Clear call to action
- Contact information placeholder""",

        'Flyer': """
- Eye-catching headline
- 3-5 key points
- Brief supporting copy
- Strong call to action
- Mark image placement areas""",

        'Conference Backdrop': """
- Primary tagline (very short, impactful)
- Secondary supporting message
- Key differentiators (2-3 words each)
- Brand positioning statement""",

        'Email Campaign': """
- Subject line options (3 alternatives)
- Preview text
- Greeting
- Opening hook
- Body with clear value proposition
- Bullet points for benefits
- Call to action button text
- Closing
- Signature block placeholder""",

        'Social Media Post': """
- Multiple post options (3-5 variations)
- Platform-appropriate length (LinkedIn: longer, Twitter: concise)
- Relevant hashtag suggestions
- Emoji suggestions where appropriate
- Call to action""",

        'Website Copy': """
- Page headline (H1)
- Subheadline
- Hero section copy
- Key benefits section with headers
- Feature descriptions
- Social proof/testimonial placeholders
- CTA sections""",

        'Case Study': """
- Title
- Executive Summary
- Customer Background
- Challenge
- Solution
- Implementation
- Results (with metrics placeholders)
- Customer Quote placeholder
- Conclusion""",

        'White Paper': """
- Title
- Executive Summary
- Table of Contents outline
- Introduction
- Problem Statement
- Detailed Solution/Approach
- Benefits and Outcomes
- Case Examples
- Conclusion
- Call to Action
- References section""",

        'Data Sheet': """
- Product Name and Version
- Product Overview (2-3 sentences)
- Key Features (bulleted list)
- Technical Specifications
- System Requirements
- Integration Capabilities
- Compliance/Certifications
- Contact Information""",

        'Sales One-Pager': """
- Headline
- Value Proposition (1-2 sentences)
- Key Benefits (3-4 bullets)
- Differentiators
- Use Cases
- Pricing/Contact CTA"""
    }

    return guidelines.get(asset_type, """
- Clear headline
- Compelling body copy
- Key benefits highlighted
- Call to action""")


def run_regulatory_check(content, brand_id, retries=3):
    """Run regulatory compliance check on content."""
    brand = get_brand_by_id(brand_id)

    # Get regulatory documents
    regulatory_docs = extract_relevant_assets_text(
        brand_id,
        ['Regulatory'],
        max_chars=6000
    )

    system_message = """You are a regulatory compliance expert specializing in healthcare and medical device marketing content review. You have deep knowledge of FDA regulations, FTC advertising guidelines, and healthcare marketing compliance requirements."""

    user_prompt = f"""Review the following marketing content for regulatory compliance issues.

CONTENT TO REVIEW:
{content}

REGULATORY GUIDELINES AND CONTEXT:
{regulatory_docs if regulatory_docs else "Apply standard FDA/healthcare marketing compliance guidelines for AI-powered medical software and digital pathology solutions."}

BRAND: {brand['brand_name']}

Please review this marketing content and identify any potential compliance issues. For each issue found, provide:

1. SEVERITY: High / Medium / Low
2. ISSUE: Brief description of the concern
3. EXCERPT: The specific text that triggered the flag
4. RECOMMENDATION: Suggested revision or action

Focus on:
- Unsubstantiated claims
- Diagnostic accuracy claims that may require FDA clearance
- Comparison claims without substantiation
- Patient outcome claims
- Safety claims
- Efficacy claims
- Off-label use suggestions
- Missing required disclaimers

If no issues are found, respond with:
"NO ISSUES FOUND - Content appears compliant with standard healthcare marketing guidelines."

Provide your analysis in a clear, structured format:"""

    client = get_openai_client()

    for attempt in range(retries):
        try:
            response = client.chat.completions.create(
                model=Config.OPENAI_MODEL,
                max_tokens=2048,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_prompt}
                ]
            )
            return response.choices[0].message.content, None
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
            else:
                return None, f"API error: {str(e)}"

    return None, "Unknown error"


def generate_design_brief(content, asset_type, brand_id, retries=3):
    """Generate a design brief for the content."""
    brand = get_brand_by_id(brand_id)

    # Get marketing materials for brand guidelines reference
    brand_guidelines = extract_relevant_assets_text(
        brand_id,
        ['Marketing Material', 'Pitch Deck'],
        max_chars=3000
    )

    system_message = """You are an experienced creative director who creates comprehensive design briefs for marketing materials. You understand healthcare and medical technology branding, and you provide detailed, actionable guidance for designers."""

    user_prompt = f"""Create a design brief for an external designer to create a {asset_type} for {brand['brand_name']}.

CONTENT TO BE DESIGNED:
{content}

EXISTING BRAND MATERIALS REFERENCE:
{brand_guidelines if brand_guidelines else "No existing materials uploaded. Apply professional healthcare/medical technology design standards."}

Create a comprehensive design brief that includes:

1. PROJECT OVERVIEW
- Asset type: {asset_type}
- Brand: {brand['brand_name']}
- Purpose and goals

2. DIMENSIONS & SPECIFICATIONS
- Recommended size/dimensions
- File format requirements
- Resolution requirements
- Bleed and safe zones (if applicable)

3. VISUAL STYLE
- Overall aesthetic direction
- Mood/feeling to convey
- Design principles to follow

4. COLOR PALETTE
- Primary colors (suggest hex codes)
- Secondary colors
- Background colors
- Text colors

5. TYPOGRAPHY
- Headline font style recommendations
- Body copy font style
- Font sizes and hierarchy

6. IMAGERY & GRAPHICS
- Types of images needed
- Image style (photography, illustration, icons)
- Specific visual elements to include
- Stock image direction if needed

7. LAYOUT GUIDANCE
- Content hierarchy
- Key focal points
- White space usage
- Grid/structure suggestions

8. BRAND GUIDELINES
- Logo placement
- Brand elements to include
- Consistency requirements

9. DELIVERABLES
- File formats needed
- Variations required
- Timeline expectations (placeholder)

10. ADDITIONAL NOTES
- Any specific requirements or constraints
- Reference examples if applicable

Format this as a professional email to the designer:

Subject: Design Brief: {asset_type} for {brand['brand_name']}

[Email body with the brief]"""

    client = get_openai_client()

    for attempt in range(retries):
        try:
            response = client.chat.completions.create(
                model=Config.OPENAI_MODEL,
                max_tokens=3000,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_prompt}
                ]
            )
            return response.choices[0].message.content, None
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
            else:
                return None, f"API error: {str(e)}"

    return None, "Unknown error"


def extract_audiences_from_document(text, brand_id, document_name, retries=3):
    """Extract target audiences from a marketing document."""
    system_message = """You are a marketing analyst who excels at identifying and categorizing target audiences from marketing documents. You return structured JSON data."""

    user_prompt = f"""Analyze this marketing document and extract all mentioned target audiences or customer segments.

DOCUMENT CONTENT:
{text[:8000]}

For each distinct audience or customer segment mentioned, provide:
1. A clear, concise name for the audience (e.g., "Pathology Lab Directors", "Hospital IT Decision Makers")
2. A brief description of their characteristics, needs, and pain points

Return the results as a JSON array with objects containing "name" and "description" fields.

Example format:
[
    {{"name": "Pathology Lab Directors", "description": "Senior pathologists managing laboratory operations, focused on efficiency, accuracy, and cost management."}},
    {{"name": "Hospital Administrators", "description": "Healthcare executives concerned with ROI, workflow optimization, and patient outcomes."}}
]

Only include audiences that are clearly identifiable customer segments. Do not include internal teams or generic references.

Return ONLY the JSON array, no other text:"""

    client = get_openai_client()

    for attempt in range(retries):
        try:
            response = client.chat.completions.create(
                model=Config.OPENAI_MODEL,
                max_tokens=1500,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_prompt}
                ]
            )

            response_text = response.choices[0].message.content.strip()

            # Clean up response if it has markdown code blocks
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]

            audiences = json.loads(response_text)
            return audiences, None

        except json.JSONDecodeError as e:
            if attempt < retries - 1:
                time.sleep(1)
            else:
                return [], f"Failed to parse audience data: {str(e)}"
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
            else:
                return [], f"API error: {str(e)}"

    return [], "Unknown error"
