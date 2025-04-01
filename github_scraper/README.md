# GitHub Contributors Scraper

A Python script that extracts GitHub repository contributors and their social profiles.

## Features

- Scrapes contributors from one or more GitHub repositories
- Extracts detailed profile information for each contributor
- Extracts LinkedIn profiles from bio and blog fields
- Saves data to a CSV file for easy analysis
- Handles rate limiting to avoid GitHub API restrictions
- Reads repository URLs from a text file
- Supports .env file for GitHub API token

## Requirements

- Python 3.6+
- `requests` library
- `python-dotenv` library

Install required packages with:

```bash
pip install -r requirements.txt
```

## Usage

### Setting Up Authentication (Recommended)

To avoid GitHub API rate limits, set up a GitHub token:

1. Create a token at https://github.com/settings/tokens
   - Only the `read:user` and `public_repo` scopes are needed
2. Copy `.env.example` to `.env` and add your token:

```bash
cp .env.example .env
# Edit .env and add your GitHub token
```

### Using a Repository List File (Default)

By default, the script reads repository URLs from a file named `repos.txt`:

```bash
python github_contributors_scraper.py
```

The `repos.txt` file should contain one repository URL per line:

```
https://github.com/username/repo1
https://github.com/username/repo2
```

Lines starting with `#` are treated as comments and will be ignored.

You can specify a different file using the `--repos-file` option:

```bash
python github_contributors_scraper.py --repos-file my_repos.txt
```

### Specifying Repositories via Command Line

You can also specify repositories directly on the command line:

```bash
python github_contributors_scraper.py --repos https://github.com/username/repo1 https://github.com/username/repo2
```

### Overriding the Token from Command Line

If you want to use a different token than the one in the .env file:

```bash
python github_contributors_scraper.py --token YOUR_GITHUB_TOKEN
```

### Specify Output File

```bash
python github_contributors_scraper.py --output custom_filename.csv
```

## Output

The script generates a CSV file with the following information for each contributor:

- Repository URL
- GitHub username
- Full name
- Email address (if public)
- Company affiliation
- Personal website/blog URL
- Location
- Bio
- Twitter username
- LinkedIn URL (extracted from bio or blog if available)
- Number of public repositories
- Number of public gists
- Follower count
- Following count
- Profile URL

## Notes

- GitHub API has rate limits (60 requests/hour for unauthenticated users, 5000 requests/hour with authentication)
- The script includes a 1-second delay between requests to respect rate limits
- Some profile information may be empty if the user hasn't provided it publicly
- LinkedIn URLs are extracted from bio and blog fields and may not be available for all users

## License

This script is provided as-is for educational purposes. 