#!/usr/bin/env python3
"""
Generate index page listing all seminars and lectures.
"""

import json
from pathlib import Path

INDEX_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Transcribed Lectures</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen',
                'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue',
                sans-serif;
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
            background: #f5f5f5;
            color: #333;
            line-height: 1.6;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem;
        }}
        
        header {{
            background: white;
            padding: 2rem;
            margin-bottom: 2rem;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        
        h1 {{
            font-size: 2.5rem;
            margin-bottom: 0.5rem;
            color: #2c3e50;
        }}
        
        .subtitle {{
            color: #7f8c8d;
            font-size: 1.1rem;
        }}
        
        .seminar-section {{
            background: white;
            margin-bottom: 2rem;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        
        .seminar-header {{
            background: #3498db;
            color: white;
            padding: 1.5rem 2rem;
            font-size: 1.5rem;
            font-weight: 600;
        }}
        
        .lectures-list {{
            padding: 0;
        }}
        
        .lecture-item {{
            border-bottom: 1px solid #ecf0f1;
            transition: background 0.2s;
        }}
        
        .lecture-item:last-child {{
            border-bottom: none;
        }}
        
        .lecture-item:hover {{
            background: #f8f9fa;
        }}
        
        .lecture-link {{
            display: block;
            padding: 1.5rem 2rem;
            text-decoration: none;
            color: #2c3e50;
            font-size: 1.1rem;
        }}
        
        .lecture-link:hover {{
            color: #3498db;
        }}
        
        .lecture-link::after {{
            content: '→';
            float: right;
            color: #95a5a6;
            font-size: 1.5rem;
        }}
        
        .lecture-link:hover::after {{
            color: #3498db;
        }}
        
        .empty-state {{
            text-align: center;
            padding: 4rem 2rem;
            color: #7f8c8d;
        }}
        
        .empty-state h2 {{
            margin-bottom: 1rem;
        }}
        
        .stats {{
            display: flex;
            gap: 2rem;
            margin-top: 1rem;
            flex-wrap: wrap;
        }}
        
        .stat {{
            background: #ecf0f1;
            padding: 0.5rem 1rem;
            border-radius: 4px;
            font-size: 0.9rem;
        }}
        
        .stat strong {{
            color: #2c3e50;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Transcribed Lectures</h1>
            <p class="subtitle">Browse and view transcripts of recorded lectures</p>
            <div class="stats">
                <div class="stat">
                    <strong>{total_seminars}</strong> Seminar{plural_seminars}
                </div>
                <div class="stat">
                    <strong>{total_lectures}</strong> Lecture{plural_lectures}
                </div>
            </div>
        </header>
        
        {seminar_sections}
    </div>
</body>
</html>
'''

SEMINAR_SECTION_TEMPLATE = '''        <div class="seminar-section">
            <div class="seminar-header">{seminar_name}</div>
            <div class="lectures-list">
{lecture_items}
            </div>
        </div>
'''

LECTURE_ITEM_TEMPLATE = '''                <div class="lecture-item">
                    <a href="{lecture_path}" class="lecture-link">{lecture_name}</a>
                </div>
'''


def generate_index_page(manifest_path: Path, output_dir: Path):
    """Generate the index HTML page."""
    # Load manifest
    with open(manifest_path, 'r', encoding='utf-8') as f:
        bundles = json.load(f)
    
    # Initialize total_lectures before the if/else block
    total_lectures = 0
    
    if not bundles:
        # Empty state
        index_html = INDEX_TEMPLATE.format(
            total_seminars=0,
            plural_seminars='s',
            total_lectures=0,
            plural_lectures='s',
            seminar_sections='<div class="empty-state"><h2>No lectures available</h2><p>Transcriptions will appear here once they are generated.</p></div>'
        )
    else:
        # Generate seminar sections
        seminar_sections = []
        
        # Sort seminars alphabetically
        for seminar_name in sorted(bundles.keys()):
            lectures = bundles[seminar_name]
            total_lectures += len(lectures)
            
            # Generate lecture items
            lecture_items = []
            # Sort lectures alphabetically
            for lecture in sorted(lectures, key=lambda x: x['name']):
                lecture_items.append(LECTURE_ITEM_TEMPLATE.format(
                    lecture_name=lecture['name'],
                    lecture_path=lecture['path']
                ))
            
            seminar_sections.append(SEMINAR_SECTION_TEMPLATE.format(
                seminar_name=seminar_name,
                lecture_items=''.join(lecture_items)
            ))
        
        index_html = INDEX_TEMPLATE.format(
            total_seminars=len(bundles),
            plural_seminars='s' if len(bundles) != 1 else '',
            total_lectures=total_lectures,
            plural_lectures='s' if total_lectures != 1 else '',
            seminar_sections='\n'.join(seminar_sections)
        )
    
    # Write index file
    with open(output_dir / "index.html", 'w', encoding='utf-8') as f:
        f.write(index_html)
    
    print(f"✅ Generated index page with {len(bundles)} seminar(s) and {total_lectures} lecture(s)")


def copy_react_transcript_editor_bundle(output_dir: Path, base_dir: Path):
    """Check if react-transcript-editor bundle exists."""
    bundle_path = output_dir / "bundles" / "react-transcript-editor-bundle.js"
    
    if not bundle_path.exists():
        print("⚠️  Warning: react-transcript-editor bundle not found.")
        print("   The bundle should be built by the GitHub Actions workflow.")
        print("   For local testing, run: node scripts/build-browser-bundle.js")
    else:
        print(f"✅ Found react-transcript-editor bundle at {bundle_path}")


def main():
    """Main entry point."""
    script_dir = Path(__file__).parent
    base_dir = script_dir.parent
    output_dir = base_dir / "gh-pages-output"
    manifest_path = output_dir / "bundles-manifest.json"
    
    if not manifest_path.exists():
        print("❌ Error: bundles-manifest.json not found. Run generate-gh-pages-bundles.py first.")
        return
    
    generate_index_page(manifest_path, output_dir)
    copy_react_transcript_editor_bundle(output_dir, base_dir)


if __name__ == "__main__":
    main()

