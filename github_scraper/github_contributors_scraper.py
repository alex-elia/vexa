#!/usr/bin/env python3
"""
GitHub Contributors Scraper

This script processes a list of GitHub repositories, extracts contributors,
and saves their social profiles to a CSV file.
"""

import csv
import os
import time
import requests
import argparse
import re
import sys
from urllib.parse import urlparse
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class GitHubScraper:
    def __init__(self, token=None, output_file="github_contributors.csv", debug=False):
        """Initialize the GitHub scraper with an optional authentication token."""
        self.headers = {}
        if token:
            self.headers["Authorization"] = f"Bearer {token}"
        
        # Rate limiting
        self.request_delay = 1  # seconds between requests to avoid hitting rate limits
        
        # Debugging
        self.debug = debug
        
        # CSV file setup
        self.output_file = output_file
        self.fieldnames = [
            "repository", "username", "name", "email", "company", 
            "blog", "location", "bio", "twitter_username", "linkedin_url",
            "public_repos", "public_gists", "followers", "following", "profile_url"
        ]
        
        # Create CSV file with headers if it doesn't exist
        if not os.path.exists(self.output_file):
            with open(self.output_file, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=self.fieldnames)
                writer.writeheader()
            print(f"Created output file: {self.output_file}")

    def get_contributors(self, repo_url):
        """Get contributors for a given repository."""
        # Parse the GitHub URL to extract owner and repo name
        parsed_url = urlparse(repo_url)
        path_parts = parsed_url.path.strip('/').split('/')
        
        if len(path_parts) < 2:
            print(f"Invalid GitHub URL: {repo_url}")
            return []
            
        owner, repo = path_parts[0], path_parts[1]
        
        # GitHub API endpoint for contributors
        api_url = f"https://api.github.com/repos/{owner}/{repo}/contributors"
        
        try:
            response = requests.get(api_url, headers=self.headers)
            response.raise_for_status()
            
            contributors = response.json()
            return contributors
        except requests.exceptions.RequestException as e:
            print(f"Error fetching contributors for {repo_url}: {str(e)}")
            return []
    
    def get_user_profile(self, username):
        """Get detailed user profile including social links."""
        api_url = f"https://api.github.com/users/{username}"
        
        try:
            response = requests.get(api_url, headers=self.headers)
            response.raise_for_status()
            
            profile = response.json()
            time.sleep(self.request_delay)  # Respect rate limits
            return profile
        except requests.exceptions.RequestException as e:
            print(f"Error fetching profile for {username}: {str(e)}")
            return {}
    
    def extract_linkedin_url(self, bio, blog, company, name, username):
        """
        Extract LinkedIn URL from user data using multiple methods:
        1. Look for LinkedIn URLs in bio text
        2. Check if blog URL is a LinkedIn profile
        3. Check company field for LinkedIn references
        """
        # Convert None values to empty strings to avoid errors
        bio = bio or ""
        blog = blog or ""
        company = company or ""
        name = name or ""
        
        # Define regex patterns for LinkedIn URLs with various formats
        linkedin_patterns = [
            r'https?://(?:www\.)?linkedin\.com/in/[\w\-\.%]+/?',
            r'https?://(?:www\.)?linkedin\.com/profile/view\?id=[\w\-_%]+',
            r'linkedin\.com/in/[\w\-\.%]+',
            r'linkedin\.com/profile/[\w\-\.%]+',
            r'linkedin\.com/pub/[\w\-\.%/]+',
            r'linkedin\.com/mwlite/in/[\w\-\.%]+',
        ]
        
        found_url = None
        source = None
        
        # Method 1: Check bio for LinkedIn URL
        if bio:
            for pattern in linkedin_patterns:
                match = re.search(pattern, bio, re.IGNORECASE)
                if match:
                    found_url = match.group(0)
                    if not found_url.startswith('http'):
                        found_url = 'https://' + found_url
                    source = "bio"
                    break
        
        # Method 2: Check if the blog URL is a LinkedIn profile
        if not found_url and blog:
            # Check if full URL matches LinkedIn patterns
            for pattern in linkedin_patterns:
                match = re.search(pattern, blog, re.IGNORECASE)
                if match:
                    found_url = match.group(0)
                    if not found_url.startswith('http'):
                        found_url = 'https://' + found_url
                    source = "blog"
                    break
            
            # Check if blog URL itself is LinkedIn
            if not found_url and 'linkedin.com' in blog.lower():
                found_url = blog
                source = "blog_domain"
        
        # Method 3: Check company field for LinkedIn references
        if not found_url and company:
            for pattern in linkedin_patterns:
                match = re.search(pattern, company, re.IGNORECASE)
                if match:
                    found_url = match.group(0)
                    if not found_url.startswith('http'):
                        found_url = 'https://' + found_url
                    source = "company"
                    break
        
        # Debug output
        if self.debug:
            if found_url:
                print(f"  - Found LinkedIn URL for {username} in {source}: {found_url}")
            else:
                print(f"  - No LinkedIn URL found for {username}")
                print(f"    Bio: {bio[:50]}{'...' if len(bio) > 50 else ''}")
                print(f"    Blog: {blog}")
                print(f"    Company: {company}")
        
        return found_url or ""
    
    def append_to_csv(self, contributor_data):
        """Append a single contributor's data to the CSV file."""
        with open(self.output_file, 'a', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=self.fieldnames)
            writer.writerow(contributor_data)
    
    def process_repos(self, repo_list):
        """Process a list of repositories and collect contributor information."""
        total_contributors = 0
        linkedin_found = 0
        
        for repo_url in repo_list:
            print(f"Processing repository: {repo_url}")
            contributors = self.get_contributors(repo_url)
            
            for contributor in contributors:
                username = contributor.get("login")
                profile = self.get_user_profile(username)
                
                name = profile.get("name", "")
                bio = profile.get("bio", "")
                blog = profile.get("blog", "")
                company = profile.get("company", "")
                
                linkedin_url = self.extract_linkedin_url(bio, blog, company, name, username)
                
                # Extract relevant profile information
                contributor_data = {
                    "repository": repo_url,
                    "username": username,
                    "name": name,
                    "email": profile.get("email", ""),
                    "company": company,
                    "blog": blog,
                    "location": profile.get("location", ""),
                    "bio": bio,
                    "twitter_username": profile.get("twitter_username", ""),
                    "linkedin_url": linkedin_url,
                    "public_repos": profile.get("public_repos", 0),
                    "public_gists": profile.get("public_gists", 0),
                    "followers": profile.get("followers", 0),
                    "following": profile.get("following", 0),
                    "profile_url": profile.get("html_url", "")
                }
                
                # Update statistics
                total_contributors += 1
                if linkedin_url:
                    linkedin_found += 1
                
                # Append data to CSV file immediately
                self.append_to_csv(contributor_data)
                print(f"  - Processed contributor: {username}" + 
                     (f" (LinkedIn: ✓)" if linkedin_url else ""))
        
        # Print summary
        linkedin_percentage = (linkedin_found / total_contributors * 100) if total_contributors > 0 else 0
        print(f"\nSummary:")
        print(f"  - Total contributors processed: {total_contributors}")
        print(f"  - LinkedIn profiles found: {linkedin_found} ({linkedin_percentage:.1f}%)")
        print(f"All data saved to {self.output_file}")

def read_repos_from_file(filename):
    """Read repository URLs from a text file."""
    repos = []
    try:
        with open(filename, 'r') as file:
            for line in file:
                repo_url = line.strip()
                if repo_url and not repo_url.startswith('#'):  # Skip empty lines and comments
                    repos.append(repo_url)
        return repos
    except Exception as e:
        print(f"Error reading repos file: {str(e)}")
        return []

def main():
    parser = argparse.ArgumentParser(description="Scrape GitHub repositories for contributor information")
    parser.add_argument("--token", help="GitHub Personal Access Token for API authentication (overrides .env)")
    parser.add_argument("--repos", nargs="+", help="List of GitHub repository URLs to process")
    parser.add_argument("--repos-file", default="repos.txt", help="File containing repository URLs (one per line)")
    parser.add_argument("--output", default="github_contributors.csv", help="Output CSV filename")
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    
    args = parser.parse_args()
    
    # Check for token in args, .env, or environment variables (in that order)
    token = args.token or os.getenv("GITHUB_TOKEN")
    if not token:
        print("Warning: No GitHub token provided in args or .env file. API rate limits will be lower.")
    else:
        print("Using GitHub token from", "command line" if args.token else ".env file")
    
    # Get repositories from command line args or from file
    repos = []
    if args.repos:
        repos = args.repos
    else:
        repos = read_repos_from_file(args.repos_file)
    
    if not repos:
        print("Error: No repositories specified. Please provide repositories via --repos or --repos-file")
        return
    
    scraper = GitHubScraper(token, args.output, args.debug)
    scraper.process_repos(repos)

if __name__ == "__main__":
    main() 