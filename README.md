# Terraform Code Assistant

A smart code assistant that helps analyze and modify Terraform configurations using AI. This project combines repository analysis with an AI-powered interface to help developers understand and modify Terraform code.

## Project Structure

project/
├── agents/
│ └── core.py # Core AI agent implementation
├── github_repo_summarizer.py # Repository analysis engine
├── main.py # Streamlit web interface
└── README.md
```

## Features

- **Repository Analysis**
  - Automatic detection and analysis of Terraform configurations
  - Dependency mapping between files
  - Resource and module tracking
  - File structure visualization
  - Comprehensive summary generation

- **AI Code Assistant**
  - Interactive chat interface
  - Context-aware code modifications
  - Intelligent path resolution
  - Support for complex Terraform structures

## Components

### 1. GitHub Repo Analyzer (`github_repo_summarizer.py`)

The core analysis engine that:
- Clones and analyzes Git repositories
- Builds dependency graphs
- Generates repository summaries
- Creates visualizations
- Handles multiple programming languages
- Special handling for Terraform configurations

Key methods:
- `analyze_repo()`: Main analysis entry point
- `print_summary()`: Generates human-readable summary
- `export_summary()`: Exports JSON-formatted data
- `visualize_structure()`: Creates repository structure diagrams
- `visualize_dependencies()`: Creates dependency graphs

### 2. AI Code Assistant (`agents/core.py`)

The AI interface that:
- Processes natural language requests
- Understands repository context
- Makes precise code modifications
- Handles path resolution

Key components:
- `Codebase` class: Main interface to the AI system
- `get_code_context()`: Retrieves file contents for context
- Path resolution system for accurate file handling

### 3. Web Interface (`main.py`)

Streamlit-based web interface that:
- Provides chat-based interaction
- Handles repository cloning
- Displays analysis results
- Manages conversation history

## Usage

### Installation

```bash
pip install -r requirements.txt
```

### Running the Application

```bash
streamlit run main.py
```

### Using the Code Assistant

1. Enter the repository URL (defaults to terraform-aws-vpc)
2. Click "Clone Repository & Summarize"
3. Wait for analysis to complete
4. Use the chat interface to request modifications

Example commands:

"Update the VPC CIDR in the outpost example to 10.0.0.0/22"
"Change the region in simple example from eu-west-1 to asia-south-1"
```

## Development

### Adding New Features

1. **Extending Analysis**
   - Add new patterns to `language_patterns` in `GitHubRepoAnalyzer`
   - Implement new analysis methods in `_analyze_dependencies`

2. **Enhancing AI Capabilities**
   - Modify the system prompt in `Codebase.__init__`
   - Add new context gathering methods

3. **UI Improvements**
   - Extend the Streamlit interface in `main.py`
   - Add new visualization options

### Path Handling

The system uses a strict path handling system:
- All paths must be absolute from repository root
- Forward slashes (/) are used even on Windows
- Paths are normalized before use
- Special handling for Terraform module paths

## Dependencies

- Python 3.8+
- Streamlit
- OpenAI API
- NetworkX
- Matplotlib
- GitPython
- PyGraphviz (optional, for advanced visualization)

## Error Handling

The system includes robust error handling for:
- Repository cloning failures
- File access issues
- Path resolution problems
- AI response processing
- Unicode encoding issues

## Contributing

1. Fork the repository
2. Create a feature branch
3. Implement changes
4. Add tests if applicable
5. Submit a pull request