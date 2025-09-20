import urllib.request
import urllib.parse
import html.parser
import csv
import os
import sys
import re
from typing import List, Dict, Optional, Union


class TableExtractor(html.parser.HTMLParser):
    """
    HTML parser that extracts table data from HTML content.
    Handles nested tables and complex HTML structures.
    """
    
    def __init__(self):
        super().__init__()
        self.tables = []
        self.current_table = []
        self.current_row = []
        self.current_cell = []
        self.in_table = False
        self.in_row = False
        self.in_cell = False
        self.in_header = False
        self.table_count = 0
        
    def handle_starttag(self, tag: str, attrs: List[tuple]) -> None:
        """Handle opening HTML tags"""
        if tag.lower() == 'table':
            self.in_table = True
            self.current_table = []
            self.table_count += 1
            
        elif tag.lower() == 'tr' and self.in_table:
            self.in_row = True
            self.current_row = []
            
        elif tag.lower() in ['td', 'th'] and self.in_row:
            self.in_cell = True
            self.in_header = (tag.lower() == 'th')
            self.current_cell = []
            
    def handle_endtag(self, tag: str) -> None:
        """Handle closing HTML tags"""
        if tag.lower() == 'table' and self.in_table:
            if self.current_table:  # Only add non-empty tables
                self.tables.append(self.current_table)
            self.in_table = False
            self.current_table = []
            
        elif tag.lower() == 'tr' and self.in_row:
            if self.current_row:  # Only add non-empty rows
                self.current_table.append(self.current_row)
            self.in_row = False
            self.current_row = []
            
        elif tag.lower() in ['td', 'th'] and self.in_cell:
            # Clean up the cell content
            cell_text = ' '.join(self.current_cell).strip()
            cell_text = re.sub(r'\s+', ' ', cell_text)  # Normalize whitespace
            self.current_row.append(cell_text)
            self.in_cell = False
            self.in_header = False
            self.current_cell = []
            
    def handle_data(self, data: str) -> None:
        """Handle text content within HTML tags"""
        if self.in_cell:
            # Clean up the data and add to current cell
            cleaned_data = data.strip()
            if cleaned_data:
                self.current_cell.append(cleaned_data)


def fetch_html_content(source: str) -> str:
    """
    Fetch HTML content from either a URL or local file.
    
    Args:
        source: URL or file path
        
    Returns:
        HTML content as string
        
    Raises:
        Exception: If unable to fetch content
    """
    try:
        # Check if it's a URL
        if source.startswith(('http://', 'https://')):
            print(f"Fetching content from URL: {source}")
            
            # Create a request with a user agent to avoid being blocked
            request = urllib.request.Request(
                source,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
            )
            
            with urllib.request.urlopen(request, timeout=30) as response:
                # Handle different encodings
                content = response.read()
                encoding = response.headers.get_content_charset() or 'utf-8'
                return content.decode(encoding, errors='replace')
                
        else:
            # Treat as local file path
            print(f"Reading content from file: {source}")
            with open(source, 'r', encoding='utf-8', errors='replace') as file:
                return file.read()
                
    except Exception as e:
        raise Exception(f"Error fetching content from {source}: {str(e)}")


def clean_filename(filename: str) -> str:
    """
    Clean filename to be filesystem-safe.
    
    Args:
        filename: Original filename
        
    Returns:
        Cleaned filename safe for filesystem
    """
    # Remove or replace invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    filename = re.sub(r'\s+', '_', filename)
    return filename[:100]  # Limit length


def extract_page_title(html_content: str) -> str:
    """
    Extract page title from HTML content for naming output files.
    
    Args:
        html_content: HTML content string
        
    Returns:
        Page title or default name
    """
    try:
        # Simple regex to extract title
        title_match = re.search(r'<title[^>]*>(.*?)</title>', html_content, re.IGNORECASE | re.DOTALL)
        if title_match:
            title = title_match.group(1).strip()
            title = re.sub(r'<[^>]+>', '', title)  # Remove any HTML tags
            title = html.parser.HTMLParser().unescape(title)  # Decode HTML entities
            return clean_filename(title)
    except:
        pass
    
    return "webpage_tables"


def save_table_to_csv(table: List[List[str]], filename: str) -> None:
    """
    Save a table to CSV file.
    
    Args:
        table: 2D list representing the table
        filename: Output filename
    """
    if not table:
        print(f"Warning: Empty table, skipping {filename}")
        return
        
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile, quoting=csv.QUOTE_MINIMAL)
            
            # Write all rows
            for row in table:
                # Ensure all cells are strings and handle empty cells
                clean_row = [str(cell) if cell else '' for cell in row]
                writer.writerow(clean_row)
                
        print(f"Successfully saved table to: {filename}")
        
    except Exception as e:
        print(f"Error saving table to {filename}: {str(e)}")


def create_output_directory(output_dir: str) -> None:
    """
    Create output directory if it doesn't exist.
    
    Args:
        output_dir: Directory path to create
    """
    try:
        os.makedirs(output_dir, exist_ok=True)
        print(f"Output directory: {output_dir}")
    except Exception as e:
        print(f"Error creating output directory {output_dir}: {str(e)}")
        raise


def print_table_summary(tables: List[List[List[str]]], page_title: str) -> None:
    """
    Print summary of extracted tables.
    
    Args:
        tables: List of tables (each table is a list of rows)
        page_title: Title of the source page
    """
    print(f"\n=== TABLE EXTRACTION SUMMARY ===")
    print(f"Source: {page_title}")
    print(f"Total tables found: {len(tables)}")
    
    for i, table in enumerate(tables, 1):
        if table:
            print(f"Table {i}: {len(table)} rows, {len(table[0])} columns")
            # Show first few column headers if available
            if table[0]:
                headers = table[0][:5]  # First 5 columns
                headers_str = ', '.join(f'"{h[:20]}..."' if len(h) > 20 else f'"{h}"' for h in headers)
                print(f"  Sample headers: {headers_str}")
        else:
            print(f"Table {i}: Empty")


def main():
    """
    Main function to run the table extraction program.
    """
    print("=== HTML Table to CSV Converter ===\n")
    
    # Handle command line arguments
    if len(sys.argv) < 2:
        print("Usage: python table_extractor.py <URL or file path> [output directory]")
        print("\nExamples:")
        print("  python table_extractor.py https://en.wikipedia.org/wiki/Comparison_of_programming_languages")
        print("  python table_extractor.py ./local_file.html ./output/")
        print("  python table_extractor.py https://example.com/data.html /tmp/tables/")
        sys.exit(1)
    
    source = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "./extracted_tables/"
    
    try:
        # Create output directory
        create_output_directory(output_dir)
        
        # Fetch HTML content
        html_content = fetch_html_content(source)
        print(f"Successfully fetched HTML content ({len(html_content)} characters)")
        
        # Extract page title for naming
        page_title = extract_page_title(html_content)
        
        # Parse HTML and extract tables
        print("Parsing HTML and extracting tables...")
        parser = TableExtractor()
        parser.feed(html_content)
        
        tables = parser.tables
        
        if not tables:
            print("No tables found in the HTML content.")
            return
        
        # Print summary
        print_table_summary(tables, page_title)
        
        # Save each table to a separate CSV file
        print(f"\nSaving tables to CSV files...")
        
        for i, table in enumerate(tables, 1):
            if table:  # Only save non-empty tables
                filename = f"{page_title}_table_{i}.csv"
                filepath = os.path.join(output_dir, filename)
                save_table_to_csv(table, filepath)
        
        print(f"\n=== EXTRACTION COMPLETE ===")
        print(f"All tables have been saved to: {output_dir}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()  
