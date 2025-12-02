#!/usr/bin/env python3
"""
Space Opera Data Trawler
Fetches space opera book data from OpenLibrary and analyzes subject trends.
"""

import requests
import json
from collections import defaultdict
from typing import List, Dict, Set, Tuple
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from datetime import datetime


def fetch_openlibrary_data() -> List[Dict]:
    """Fetch space opera books from OpenLibrary API."""
    url = "https://openlibrary.org/search.json"
    params = {
        "q": 'subject:"space opera" AND language:eng',
        "fields": "title,author_name,subject,first_publish_year,number_of_pages_median",
        "limit": 50
    }
    
    response = requests.get(url, params=params)
    print(f"Request URL: {response.url}")
    print(f"HTTP Status Code: {response.status_code}")
    response.raise_for_status()
    data = response.json()
    return data.get("docs", [])


def is_star_wars_book(book: Dict) -> bool:
    """Check if a book is Star Wars related."""
    title = book.get("title", "").lower()
    subjects = [s.lower() for s in book.get("subject", [])]
    STAR_WARS_KEYWORD = "star wars"

    # Check title
    if STAR_WARS_KEYWORD in title:
        return True

    # Check subjects
    for subject in subjects:
        if STAR_WARS_KEYWORD in subject:
            return True
    
    return False


def should_remove_subject(subject: str) -> bool:
    """
    Determine if a subject should be removed based on filtering rules.
    Returns True if subject should be removed.
    """
    subject_lower = subject.lower()
    
    # Remove fictional characters and places
    if "(fictitious character)" in subject_lower:
        return True
    if "(imaginary place)" in subject_lower:
        return True
    
    # Remove NYT and Hugo Award related
    if "nyt:" in subject_lower or "new york times" in subject_lower:
        return True
    if "hugo award" in subject_lower or "hugo_award" in subject_lower or "award:" in subject_lower:
        return True
    
    # Remove this specific generic subject
    if "Fiction in English, 1900- Texts" in subject_lower:
        return True

    # Remove subject if there's nothing in the subject but generic genres that are supersets of the space opera subgenre.
    import string
    s = subject_lower
    # Remove key words
    for word in ["science fiction", "science-fiction", "fiction", "space opera", "general"]:
        s = s.replace(word, "")
    # Remove all punctuation and whitespace
    s = s.translate(str.maketrans('', '', string.punctuation)).strip()
    # After removing, if nothing is left, return True
    if s == "":
        return True

    return False


def filter_subjects(book: Dict) -> List[str]:
    """Filter subjects for a book according to the rules."""
    subjects = book.get("subject", [])
    filtered = []
    
    for subject in subjects:
        if not should_remove_subject(subject):
            filtered.append(subject)
    
    return filtered


def analyze_subjects(books: List[Dict]) -> Dict[str, Dict]:
    """
    Analyze subjects across books.
    Returns dict mapping subject -> {count: int, years: List[int], min_year: int, max_year: int}
    """
    subject_data = defaultdict(lambda: {"count": 0, "years": []})
    
    for book in books:
        year = book.get("first_publish_year")
        if not year:
            continue
        
        filtered_subjects = filter_subjects(book)
        for subject in filtered_subjects:
            subject_data[subject]["count"] += 1
            subject_data[subject]["years"].append(year)
    
    # Calculate min/max years and average
    result = {}
    for subject, data in subject_data.items():
        if data["count"] >= 3:  # Remove subjects with < 3 occurrences
            years = data["years"]
            result[subject] = {
                "count": data["count"],
                "min_year": min(years),
                "max_year": max(years),
                "avg_year": (min(years) + max(years)) / 2.0
            }
    for subject, data in result.items():
        print(f"Subject: {subject}")
        print(f"  Count: {data['count']}")
        print(f"  Min Year: {data['min_year']}")
        print(f"  Max Year: {data['max_year']}")
        print(f"  Avg Year: {data['avg_year']:.2f}")
    return result


def create_bar_chart(subject_data: Dict[str, Dict], title: str, filename: str):
    """Create a horizontal bar chart showing subjects over time."""
    # Sort by average year
    sorted_subjects = sorted(subject_data.items(), key=lambda x: x[1]["avg_year"])
    
    if not sorted_subjects:
        print(f"No subjects to plot for {title}")
        return
    
    subjects = [s[0] for s in sorted_subjects]
    min_years = [s[1]["min_year"] for s in sorted_subjects]
    max_years = [s[1]["max_year"] for s in sorted_subjects]
    counts = [s[1]["count"] for s in sorted_subjects]
    
    fig, ax = plt.subplots(figsize=(14, max(8, len(subjects) * 0.4)))
    
    # Create horizontal bars
    y_pos = range(len(subjects))
    
    # Plot bars showing time range
    for i, (subject, min_year, max_year) in enumerate(zip(subjects, min_years, max_years)):
        width = max_year - min_year
        ax.barh(i, width, left=min_year, alpha=0.6, height=0.8)
    
    # Add count labels
    for i, (subject, count, max_year) in enumerate(zip(subjects, counts, max_years)):
        ax.text(max_year + 1, i, f"({count})", va='center', fontsize=9)
    
    ax.set_yticks(y_pos)
    ax.set_yticklabels(subjects)
    ax.set_xlabel('Year', fontsize=12)
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.grid(axis='x', alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(filename, dpi=150, bbox_inches='tight')
    print(f"Saved chart to {filename}")
    plt.close()


def main():
    """Main execution function."""
    print("Fetching data from OpenLibrary...")
    books = fetch_openlibrary_data()
    print(f"Found {len(books)} books")
    
    # Separate into Star Wars and non-Star Wars
    star_wars_books = []
    other_books = []
    
    for book in books:
        if is_star_wars_book(book):
            star_wars_books.append(book)
        else:
            other_books.append(book)
    
    print(f"\nStar Wars books: {len(star_wars_books)}")
    print(f"Other books: {len(other_books)}")
    
    # Analyze subjects for each group
    print("\nAnalyzing Star Wars books...")
    star_wars_subjects = analyze_subjects(star_wars_books)
    print(f"Found {len(star_wars_subjects)} subjects (appearing 3+ times)")
    
    print("\nAnalyzing other books...")
    other_subjects = analyze_subjects(other_books)
    print(f"Found {len(other_subjects)} subjects (appearing 3+ times)")
    
    # Create charts
    print("\nGenerating charts...")
    create_bar_chart(star_wars_subjects, "Star Wars Books - Subject Trends Over Time", "star_wars_subjects.png")
    create_bar_chart(other_subjects, "Non-Star Wars Space Opera Books - Subject Trends Over Time", "other_space_opera_subjects.png")
    
    print("\nAnalysis complete!")


if __name__ == "__main__":
    main()

