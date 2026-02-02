# Deciphex Content Studio

A private web application for Deciphex's marketing team to generate branded marketing content using AI. The app is locally hosted, password-protected, and learns from uploaded brand materials to create on-brand content with regulatory checking.

## Features

- **Brand Asset Management**: Upload and organize brand materials (PDFs, DOCX, TXT, PPTX) for each brand
- **AI Content Generation**: Generate various marketing content types using Claude AI
- **Regulatory Checker**: Automatically review generated content for compliance issues
- **Design Brief Generator**: Create comprehensive design briefs for external designers
- **Audience Extraction**: Automatically extract target audiences from marketing materials
- **Multi-Brand Support**: Manage content for Deciphex, Diagnexia, Diagnexia Analytix, and Patholytix
- **User Management**: Admin panel for managing team members

## Supported Content Types

- Brochure
- Postcard
- Flyer
- Conference Backdrop
- Email Campaign
- Social Media Post
- Website Copy
- Case Study
- White Paper
- Data Sheet
- Sales One-Pager

## Prerequisites

- Python 3.8+
- pip (Python package manager)
- Anthropic API key

## Installation

1. **Clone or download the repository**

```bash
cd deciphex-content-studio
```

2. **Create a virtual environment (recommended)**

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
```

4. **Configure environment variables**

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` and add your Anthropic API key:

```
ANTHROPIC_API_KEY=your_anthropic_api_key_here
SECRET_KEY=your_secret_key_here
```

5. **Run the application**

```bash
python app.py
```

6. **Access the application**

Open your browser and navigate to: `http://localhost:5000`

## First-Time Setup

1. **Log in with default admin credentials**
   - Username: `admin`
   - Password: `deciphex2025`

2. **Change the default password** (you'll be prompted automatically)

3. **Add team members** through the Admin panel

4. **Upload initial brand assets** for each brand

5. **Start creating content!**

## Project Structure

```
deciphex-content-studio/
├── app.py                 # Main Flask application
├── config.py              # Configuration settings
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables (create from .env.example)
├── templates/             # HTML templates
│   ├── base.html
│   ├── login.html
│   ├── dashboard.html
│   ├── brand_assets.html
│   ├── upload_assets.html
│   ├── create_content.html
│   ├── review_content.html
│   ├── audiences.html
│   ├── admin.html
│   ├── change_password.html
│   └── error.html
├── static/                # Static assets
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── main.js
├── uploads/               # Brand asset storage (auto-created)
├── database/              # SQLite database (auto-created)
└── utils/                 # Helper functions
    ├── __init__.py
    ├── database.py
    ├── file_processor.py
    └── ai_generator.py
```

## Usage Guide

### Uploading Brand Assets

1. Select a brand from the dashboard
2. Click "Upload Assets"
3. Choose a file (PDF, DOCX, TXT, or PPTX)
4. Select the asset category (Internal/External)
5. Select the asset type (Regulatory, Pitch Deck, etc.)
6. Add an optional description
7. Click "Upload Asset"

**Tip**: Uploading "Marketing Material" type assets will automatically extract target audiences for use in content generation.

### Creating Content

1. Select a brand from the dashboard
2. Click "Create Content"
3. Choose the content type (Brochure, Email, etc.)
4. Select or enter a target audience
5. Add any additional context or requirements
6. Click "Generate Content"

### Reviewing Content

After content is generated, you can:

- **Copy to Clipboard**: Copy the generated content
- **Run Regulatory Check**: Review content for compliance issues
- **Generate Design Brief**: Create a design specification for designers

### Managing Audiences

1. Navigate to a brand's "Audiences" page
2. View automatically extracted audiences
3. Add, edit, or delete custom audiences

## Security Considerations

- Never commit the `.env` file to version control
- Change the default admin password immediately
- Use HTTPS when deploying beyond localhost
- Session timeout is set to 60 minutes

## API Configuration

The application uses Claude claude-sonnet-4-5-20250929 by default. To change the model, edit `config.py`:

```python
CLAUDE_MODEL = 'claude-sonnet-4-5-20250929'  # or another Claude model
```

## Troubleshooting

### API Key Issues
- Ensure your `ANTHROPIC_API_KEY` is correctly set in the `.env` file
- Verify the API key is valid and has sufficient credits

### File Upload Issues
- Maximum file size is 50MB
- Supported formats: PDF, DOCX, TXT, PPTX
- Ensure the `uploads` directory is writable

### Database Issues
- Delete `database/content_studio.db` to reset the database
- The database and default data will be recreated on next startup

## License

Private - Deciphex Internal Use Only

## Support

For issues or questions, contact the Deciphex IT team.
