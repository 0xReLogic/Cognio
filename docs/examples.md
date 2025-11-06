# Usage Examples

Real-world examples and patterns for using Cognio effectively.

## Table of Contents

- [Basic Usage](#basic-usage)
- [Project Organization](#project-organization)
- [Semantic Search Patterns](#semantic-search-patterns)
- [Data Management](#data-management)
- [Integration Examples](#integration-examples)
- [Advanced Patterns](#advanced-patterns)
- [Text Summarization](#text-summarization)

## Basic Usage

### Save Your First Memory

```bash
curl -X POST http://localhost:8080/memory/save \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Python uses indentation for code blocks instead of braces",
    "project": "PYTHON_LEARNING",
    "tags": ["python", "syntax", "basics"]
  }'
```

### Search for It

```bash
curl -X POST http://localhost:8080/memory/search \
  -H "Content-Type: application/json" \
  -d '{"query": "how does Python handle code blocks", "limit": 3}'
```

The semantic search will find this memory even though the query uses different words!

## Project Organization

### Personal Knowledge Base

```bash
# Save learning notes
curl -X POST http://localhost:8080/memory/save \
  -H "Content-Type: application/json" \
  -d '{
    "text": "React hooks let you use state in functional components",
    "project": "WEB_LEARNING",
    "tags": ["react", "javascript", "hooks"]
  }'

# Save work notes
curl -X POST http://localhost:8080/memory/save \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Production API endpoint: https://api.company.com/v1",
    "project": "WORK_REFERENCES",
    "tags": ["api", "production", "endpoint"]
  }'

# Save personal reminders
curl -X POST http://localhost:8080/memory/save \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Dentist appointment next Tuesday at 2 PM",
    "project": "PERSONAL",
    "tags": ["appointment", "health"]
  }'
```

### Multi-Project Workflow

```bash
# List all projects
curl http://localhost:8080/memory/stats | jq '.by_project'

# Browse specific project
curl "http://localhost:8080/memory/list?project=WORK_REFERENCES&limit=20"

# Search within project
curl -X POST http://localhost:8080/memory/search \
  -H "Content-Type: application/json" \
  -d '{"query": "API configuration", "project": "WORK_REFERENCES"}'
```

## Semantic Search Patterns

### Natural Language Queries

Instead of keyword search, ask questions naturally:

```bash
# Instead of: "fastapi cors configuration"
curl -X POST http://localhost:8080/memory/search \
  -H "Content-Type: application/json" \
  -d '{"query": "how to enable cross-origin requests in FastAPI"}'

# Instead of: "python async await"
curl -X POST http://localhost:8080/memory/search \
  -H "Content-Type: application/json" \
  -d '{"query": "what is async programming in Python"}'

# Instead of: "git rebase"
curl -X POST http://localhost:8080/memory/search \
  -H "Content-Type: application/json" \
  -d '{"query": "how to combine multiple git commits"}'
```

### Adjusting Relevance Threshold

```bash
# Strict matching (only very relevant results)
curl -X POST http://localhost:8080/memory/search \
  -H "Content-Type: application/json" \
  -d '{"query": "machine learning", "threshold": 0.85}'

# Broad matching (more results, less precise)
curl -X POST http://localhost:8080/memory/search \
  -H "Content-Type: application/json" \
  -d '{"query": "AI concepts", "threshold": 0.5}'
```

### Date-Filtered Search

```bash
# Find recent memories
curl -X POST http://localhost:8080/memory/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "API endpoints",
    "after_date": "2025-01-01"
  }'

# Find memories from specific time range
curl -X POST http://localhost:8080/memory/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "project meetings",
    "after_date": "2025-01-01",
    "before_date": "2025-01-31"
  }'
```

## Data Management

### Backup Workflow

```bash
#!/bin/bash
# backup_memories.sh

DATE=$(date +%Y%m%d)
PROJECT=$1

if [ -z "$PROJECT" ]; then
  # Backup all memories
  curl "http://localhost:8080/memory/export?format=json" > "backup_all_${DATE}.json"
else
  # Backup specific project
  curl "http://localhost:8080/memory/export?format=json&project=${PROJECT}" > "backup_${PROJECT}_${DATE}.json"
fi

echo "Backup saved to backup_${PROJECT:-all}_${DATE}.json"
```

Usage:
```bash
./backup_memories.sh                  # Backup all
./backup_memories.sh WORK_REFERENCES  # Backup project
```

### Bulk Import

```python
# bulk_import.py
import requests
import json

def import_memories(file_path, project=None):
    with open(file_path, 'r') as f:
        memories = json.load(f)['memories']
    
    for memory in memories:
        response = requests.post(
            'http://localhost:8080/memory/save',
            json={
                'text': memory['text'],
                'project': project or memory.get('project'),
                'tags': memory.get('tags', [])
            }
        )
        print(f"Saved: {memory['id']} -> {response.json()['id']}")

# Usage
import_memories('backup_all_20250105.json')
```

### Archive Old Memories

```bash
# Archive single memory
curl -X POST http://localhost:8080/memory/{memory-id}/archive \
  -H "X-API-Key: your-key"

# Bulk delete old project
curl -X POST http://localhost:8080/memory/bulk-delete \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-key" \
  -d '{"project": "OLD_PROJECT_2024"}'

# Delete memories older than 1 year
curl -X POST http://localhost:8080/memory/bulk-delete \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-key" \
  -d '{"before_date": "2024-01-01"}'
```

## Integration Examples

### Python Integration

```python
# cognio_helper.py
import requests
from typing import List, Dict, Optional

class CognioMemory:
    def __init__(self, base_url: str = "http://localhost:8080", api_key: Optional[str] = None):
        self.base_url = base_url
        self.headers = {"X-API-Key": api_key} if api_key else {}
    
    def remember(self, text: str, project: str = None, tags: List[str] = None) -> Dict:
        """Save a memory."""
        response = requests.post(
            f"{self.base_url}/memory/save",
            json={"text": text, "project": project, "tags": tags or []},
            headers=self.headers
        )
        return response.json()
    
    def recall(self, query: str, project: str = None, limit: int = 5) -> List[Dict]:
        """Search memories."""
        response = requests.post(
            f"{self.base_url}/memory/search",
            json={"query": query, "project": project, "limit": limit}
        )
        return response.json()['results']
    
    def forget(self, memory_id: str) -> bool:
        """Delete a memory."""
        response = requests.delete(
            f"{self.base_url}/memory/{memory_id}",
            headers=self.headers
        )
        return response.json()['deleted']

# Usage
memory = CognioMemory(api_key="your-key")

# Save
result = memory.remember(
    "FastAPI uses Pydantic for data validation",
    project="LEARNING",
    tags=["fastapi", "python", "validation"]
)
print(f"Saved: {result['id']}")

# Search
results = memory.recall("how does FastAPI validate data", limit=3)
for r in results:
    print(f"[{r['score']:.2f}] {r['text']}")
```

### Shell Script Integration

```bash
#!/bin/bash
# memory_note.sh - Quick note saver

PROJECT=${1:-NOTES}
shift
TEXT="$@"

if [ -z "$TEXT" ]; then
  echo "Usage: memory_note.sh [PROJECT] <text>"
  exit 1
fi

curl -X POST http://localhost:8080/memory/save \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${COGNIO_API_KEY}" \
  -d "{\"text\": \"$TEXT\", \"project\": \"$PROJECT\", \"tags\": [\"note\"]}" \
  | jq -r '.id'
```

Usage:
```bash
export COGNIO_API_KEY=your-key
./memory_note.sh LEARNING "Python list comprehensions are faster than loops"
./memory_note.sh "Default project note"
```

### Claude Desktop Integration

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "cognio": {
      "command": "node",
      "args": ["/path/to/cognio-mcp-bridge.js"],
      "env": {
        "COGNIO_URL": "http://localhost:8080",
        "COGNIO_API_KEY": "your-key"
      }
    }
  }
}
```

Then in Claude:
```
User: Remember that Python uses snake_case for functions
Claude: [Saves to Cognio] I've remembered that!

User: What did I learn about Python naming?
Claude: [Searches Cognio] You learned that Python uses snake_case for functions.
```

## Advanced Patterns

### Contextual Memory Retrieval

```python
def get_context(topic: str, max_context: int = 3) -> str:
    """Get relevant context for a topic from memory."""
    response = requests.post(
        'http://localhost:8080/memory/search',
        json={'query': topic, 'limit': max_context, 'threshold': 0.6}
    )
    
    memories = response.json()['results']
    context = "\n\n".join([m['text'] for m in memories])
    return f"Relevant context:\n{context}"

# Use in AI prompts
topic = "FastAPI middleware"
context = get_context(topic)
prompt = f"{context}\n\nQuestion: How do I add custom middleware in FastAPI?"
```

### Incremental Learning Journal

```python
import datetime

def daily_learning(learnings: List[str], project: str = "DAILY_LEARNING"):
    """Save daily learnings with timestamp."""
    date = datetime.date.today().isoformat()
    
    for learning in learnings:
        text = f"[{date}] {learning}"
        requests.post(
            'http://localhost:8080/memory/save',
            json={
                'text': text,
                'project': project,
                'tags': ['learning', date]
            }
        )

# Usage
daily_learning([
    "Learned about FastAPI dependency injection",
    "Discovered SQLAlchemy async support",
    "Read about Docker multi-stage builds"
])
```

### Smart Tag Suggestions

```python
def suggest_tags(text: str) -> List[str]:
    """Suggest tags based on similar memories."""
    # Search for similar memories
    response = requests.post(
        'http://localhost:8080/memory/search',
        json={'query': text, 'limit': 5}
    )
    
    # Collect tags from similar memories
    all_tags = []
    for result in response.json()['results']:
        all_tags.extend(result.get('tags', []))
    
    # Return most common tags
    from collections import Counter
    tag_counts = Counter(all_tags)
    return [tag for tag, _ in tag_counts.most_common(5)]

# Usage
text = "FastAPI supports async database operations"
suggested = suggest_tags(text)
print(f"Suggested tags: {suggested}")
```

### Memory Cleanup

```python
def cleanup_duplicates():
    """Find and archive near-duplicate memories."""
    response = requests.get('http://localhost:8080/memory/list?limit=1000')
    memories = response.json()['memories']
    
    seen_texts = {}
    duplicates = []
    
    for memory in memories:
        text_lower = memory['text'].lower().strip()
        if text_lower in seen_texts:
            duplicates.append(memory['id'])
        else:
            seen_texts[text_lower] = memory['id']
    
    # Archive duplicates
    for dup_id in duplicates:
        requests.post(
            f'http://localhost:8080/memory/{dup_id}/archive',
            headers={'X-API-Key': 'your-key'}
        )
    
    print(f"Archived {len(duplicates)} duplicates")

cleanup_duplicates()
```

## Best Practices

### 1. Consistent Project Naming

```bash
# Good - Consistent naming
PYTHON_LEARNING
WEB_DEVELOPMENT
WORK_PROJECT_X

# Avoid - Inconsistent
python-learning
webDev
work/project-x
```

### 2. Effective Tagging

```bash
# Good - Specific and consistent
["python", "async", "programming"]
["react", "hooks", "state-management"]

# Avoid - Too generic or too many
["programming", "code", "tech", "software", "development", "python", "web"]
```

### 3. Memory Text Format

```bash
# Good - Clear and concise
"FastAPI uses Pydantic models for request/response validation"

# Avoid - Too verbose or unclear
"I learned today that when you're using FastAPI framework in Python programming language..."
```

### 4. Regular Maintenance

```python
# Weekly cleanup script
import requests
from datetime import datetime, timedelta

def weekly_maintenance():
    # Export backup
    response = requests.get('http://localhost:8080/memory/export?format=json')
    with open(f'backup_{datetime.now():%Y%m%d}.json', 'w') as f:
        f.write(response.text)
    
    # Get stats
    stats = requests.get('http://localhost:8080/memory/stats').json()
    print(f"Total memories: {stats['total_memories']}")
    print(f"Storage: {stats['storage_mb']:.2f} MB")
    
    # Archive old test data
    one_year_ago = (datetime.now() - timedelta(days=365)).isoformat()
    requests.post(
        'http://localhost:8080/memory/bulk-delete',
        json={'project': 'TEST', 'before_date': one_year_ago},
        headers={'X-API-Key': 'your-key'}
    )

weekly_maintenance()
```

## Text Summarization

### Summarize Long Articles

```bash
# Summarize research paper abstract
curl -X POST http://localhost:8080/memory/summarize \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Machine learning has revolutionized artificial intelligence by enabling computers to learn from data without explicit programming. Deep learning, a subset of machine learning, uses neural networks with multiple layers to model complex patterns. Convolutional neural networks excel at image recognition tasks, while recurrent neural networks handle sequential data like text and speech. Transformer architectures have achieved breakthrough results in natural language processing, powering modern applications like chatbots and translation systems.",
    "num_sentences": 2
  }'
```

**Response**:
```json
{
  "summary": "Machine learning enables computers to learn from data without explicit programming, with deep learning using multi-layered neural networks for complex pattern modeling. Transformer architectures have achieved breakthrough results in natural language processing applications.",
  "original_length": 67,
  "summary_length": 30,
  "method": "abstractive"
}
```

### Summarize Before Saving

```python
import requests

def save_with_summary(text, project):
    # Get summary first
    summary_response = requests.post(
        'http://localhost:8080/memory/summarize',
        json={'text': text, 'num_sentences': 2}
    )
    summary_data = summary_response.json()
    
    # Save both full text and summary
    requests.post(
        'http://localhost:8080/memory/save',
        json={
            'text': summary_data['summary'],
            'project': project,
            'tags': ['summary', 'condensed']
        }
    )
    
    print(f"Condensed {summary_data['original_length']} words to {summary_data['summary_length']}")
    return summary_data

# Use it
long_article = """
Artificial intelligence is transforming industries worldwide...
[... 500 more words ...]
"""

save_with_summary(long_article, 'AI_RESEARCH')
```

### Batch Summarization

```python
import requests

def summarize_batch(texts, num_sentences=3):
    """Summarize multiple texts efficiently."""
    summaries = []
    
    for text in texts:
        response = requests.post(
            'http://localhost:8080/memory/summarize',
            json={'text': text, 'num_sentences': num_sentences}
        )
        summaries.append(response.json())
    
    return summaries

# Summarize multiple documents
documents = [
    "Long document 1...",
    "Long document 2...",
    "Long document 3..."
]

results = summarize_batch(documents, num_sentences=2)
for i, result in enumerate(results):
    print(f"Doc {i+1}: {result['summary_length']} words (from {result['original_length']})")
```

### Auto-Summarize on Save

```python
import requests

class SmartMemoryClient:
    def __init__(self, base_url="http://localhost:8080", threshold=100):
        self.base_url = base_url
        self.threshold = threshold  # Summarize if longer than this
    
    def save(self, text, project, tags):
        # Auto-summarize long texts
        word_count = len(text.split())
        
        if word_count > self.threshold:
            # Get summary
            summary_response = requests.post(
                f"{self.base_url}/memory/summarize",
                json={'text': text, 'num_sentences': 3}
            )
            text_to_save = summary_response.json()['summary']
            tags = tags + ['auto-summarized']
        else:
            text_to_save = text
        
        # Save memory
        response = requests.post(
            f"{self.base_url}/memory/save",
            json={'text': text_to_save, 'project': project, 'tags': tags}
        )
        return response.json()

# Usage
client = SmartMemoryClient(threshold=50)
client.save("Very long article...", "LEARNING", ["ai", "ml"])
# Automatically summarized if > 50 words
```

## More Examples

See the `examples/` directory for:
- `basic_usage.py` - Python client examples
- `curl_examples.sh` - Complete cURL examples
- `mcp_config.json` - MCP client configuration

## Need Help?

- [API Documentation](api.md) - Complete API reference
- [Quick Start](quickstart.md) - Get started in 5 minutes
- [GitHub Issues](https://github.com/0xReLogic/Cognio/issues) - Report bugs
- [GitHub Discussions](https://github.com/0xReLogic/Cognio/discussions) - Ask questions
