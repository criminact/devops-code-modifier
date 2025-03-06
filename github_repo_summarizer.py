import os
import re
import argparse
import subprocess
import json
from collections import defaultdict
import networkx as nx
from pathlib import Path
import matplotlib.pyplot as plt

class GitHubRepoAnalyzer:
    def __init__(self, repo_url=None, local_path=None):
        self.repo_url = repo_url
        self.local_path = local_path
        self.file_structure = {}
        self.dependencies = defaultdict(list)
        self.ignored_dirs = ['.git', 'node_modules', '__pycache__', 'venv', '.env', '.venv']
        self.language_patterns = {
            'python': {
                'files': ['.py'],
                'import_patterns': [
                    r'(?:from|import)\s+([\w.]+)',
                    r'(?:from)\s+([\w.]+)(?:\s+import)'
                ]
            },
            'javascript': {
                'files': ['.js', '.jsx', '.ts', '.tsx'],
                'import_patterns': [
                    r'(?:import|require)\s*\(?[\'\"](.+?)[\'\"]',
                    r'(?:from)\s+[\'\"](.+?)[\'\"]'
                ]
            },
            'java': {
                'files': ['.java'],
                'import_patterns': [
                    r'import\s+([\w.]+)(?:;|\s)'
                ]
            },
            'go': {
                'files': ['.go'],
                'import_patterns': [
                    r'import\s+\(\s*[\'\"](.+?)[\'\"]',
                    r'import\s+[\'\"](.+?)[\'\"]'
                ]
            },
            'terraform': {
                'files': ['.tf', '.tfvars'],
                'import_patterns': [
                    r'source\s*=\s*[\"\'](.+?)[\"\']',
                    r'module\s+[\"\'](.+?)[\"\']',
                    r'terraform\s*{\s*.*?source\s*=\s*[\"\'](.+?)[\"\']'
                ]
            }
        }
        
    def clone_repo(self, target_dir=None):
        """Clone the repository to local path"""
        if not target_dir:
            target_dir = os.path.basename(self.repo_url).replace('.git', '')
            
        try:
            print(f"Cloning {self.repo_url} to {target_dir}...")
            subprocess.run(['git', 'clone', self.repo_url, target_dir], check=True)
            self.local_path = target_dir
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error cloning repository: {e}")
            return False
            
    def analyze_repo(self):
        """Analyze the repository structure and dependencies"""
        if not self.local_path or not os.path.exists(self.local_path):
            print("Repository path does not exist.")
            return False
            
        print(f"Analyzing repository at {self.local_path}...")
        self._analyze_dependencies()  # Analyze dependencies first
        self._build_file_structure()  # Then build file structure with dependencies
        return True
        
    def _build_file_structure(self):
        """Build a dictionary representing the file structure with dependencies included"""
        self.file_structure = {}
        
        # Helper function to set a value in a nested dictionary
        def set_nested_dict(d, path, key, value):
            current = d
            for part in path:
                if part not in current:
                    current[part] = {}
                current = current[part]
            current[key] = value
        
        # Walk through all files
        for root, dirs, files in os.walk(self.local_path):
            # Skip ignored directories
            dirs[:] = [d for d in dirs if d not in self.ignored_dirs and not d.startswith('.')]
            
            # Get relative path
            rel_path = os.path.relpath(root, self.local_path)
            path_parts = [] if rel_path == '.' else rel_path.split(os.sep)
            
            # Add files at this level with their dependencies
            for file in files:
                file_path = os.path.join(root, file)
                rel_file_path = os.path.relpath(file_path, self.local_path)
                
                # Include dependencies if they exist
                file_deps = self.dependencies.get(rel_file_path, [])
                if file_deps:
                    file_data = {"dependencies": file_deps}
                    set_nested_dict(self.file_structure, path_parts, file, file_data)
                else:
                    # If no dependencies, store as empty object instead of null
                    set_nested_dict(self.file_structure, path_parts, file, {})
                
    def _get_language_from_extension(self, filename):
        """Determine the language based on file extension"""
        extension = os.path.splitext(filename)[1].lower()
        for lang, patterns in self.language_patterns.items():
            if extension in patterns['files']:
                return lang
        return None
        
    def _analyze_dependencies(self):
        """Analyze dependencies between files"""
        self.dependencies = defaultdict(list)
        
        # Walk through all files
        for root, dirs, files in os.walk(self.local_path):
            # Skip ignored directories
            if any(ignored in root for ignored in self.ignored_dirs):
                continue
                
            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, self.local_path)
                
                # Determine language
                language = self._get_language_from_extension(file)
                if not language:
                    continue
                    
                # Get import patterns for the language
                import_patterns = self.language_patterns[language]['import_patterns']
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    for pattern in import_patterns:
                        matches = re.findall(pattern, content)
                        for match in matches:
                            # Resolve to absolute path
                            resolved_path = self._resolve_absolute_import(rel_path, match)
                            if resolved_path:
                                # Store absolute path if resolved
                                self.dependencies[rel_path].append(resolved_path)
                except (UnicodeDecodeError, IOError):
                    # Skip binary or unreadable files
                    continue
                    
                # Special handling for Terraform files
                if language == 'terraform':
                    self._analyze_terraform_dependencies(file_path, rel_path, content)
    
    def _analyze_terraform_dependencies(self, file_path, rel_path, content):
        """Analyze Terraform-specific dependencies"""
        # Find module blocks
        module_blocks = re.findall(r'module\s+\"([^\"]+)\"\s+{([^}]+)}', content, re.DOTALL)
        for module_name, module_content in module_blocks:
            # Extract source attribute
            source_match = re.search(r'source\s*=\s*\"([^\"]+)\"', module_content)
            if source_match:
                module_source = source_match.group(1)
                
                # Resolve module path to absolute path
                resolved_module_path = self._resolve_absolute_import(rel_path, module_source)
                
                if resolved_module_path:
                    # Store module dependency with resolved absolute path
                    module_dependency = f"module:{module_name}:{resolved_module_path}"
                    self.dependencies[rel_path].append(module_dependency)
                
        # Find resource blocks
        resource_blocks = re.findall(r'resource\s+\"([^\"]+)\"\s+\"([^\"]+)\"\s+{', content)
        for resource_type, resource_name in resource_blocks:
            # Keep as-is since these are internal resource references
            self.dependencies[rel_path].append(f"resource:{resource_type}:{resource_name}")
            
        # Find data blocks
        data_blocks = re.findall(r'data\s+\"([^\"]+)\"\s+\"([^\"]+)\"\s+{', content)
        for data_type, data_name in data_blocks:
            # Keep as-is since these are internal data source references
            self.dependencies[rel_path].append(f"data:{data_type}:{data_name}")
            
        # Find variable references
        var_refs = re.findall(r'var\.([a-zA-Z0-9_-]+)', content)
        for var_name in var_refs:
            # Keep as-is since these are internal variable references
            self.dependencies[rel_path].append(f"var:{var_name}")
    
    def generate_summary(self):
        """Generate a summary of the repository"""
        summary = {
            "file_count": self._count_files(self.file_structure),
            "directory_count": self._count_directories(self.file_structure),
            "file_types": self._count_file_types(),
            "structure": self.file_structure
            # Dependencies are now integrated into the structure
        }
        return summary
        
    def _count_files(self, structure):
        """Count the total number of files in the structure"""
        count = 0
        for key, value in structure.items():
            if isinstance(value, dict) and not any(k for k in value.keys() if isinstance(value[k], dict)):
                # It's a file if it has no nested dictionaries other than possibly dependencies
                count += 1
            else:  # Directory
                count += self._count_files(value)
        return count
        
    def _count_directories(self, structure):
        """Count the total number of directories in the structure"""
        count = 0
        for key, value in structure.items():
            if isinstance(value, dict) and any(k for k in value.keys() if isinstance(value[k], dict)):
                # It's a directory if it has nested dictionaries
                count += 1
                count += self._count_directories(value)
        return count
        
    def _count_file_types(self):
        """Count the occurrences of each file extension"""
        extensions = {}
        
        for root, dirs, files in os.walk(self.local_path):
            if any(ignored in root for ignored in self.ignored_dirs):
                continue
                
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext:
                    extensions[ext] = extensions.get(ext, 0) + 1
                    
        return extensions
        
    def visualize_structure(self, output_file="repo_structure.png"):
        """Visualize the repository structure as a tree diagram"""
        G = nx.DiGraph()
        
        def add_nodes(structure, parent=None, path=""):
            for key, value in structure.items():
                current_path = os.path.join(path, key)
                if parent is None:  # Root node
                    G.add_node(current_path, label=key)
                else:
                    G.add_node(current_path, label=key)
                    G.add_edge(parent, current_path)
                    
                if isinstance(value, dict) and any(isinstance(value[k], dict) for k in value.keys()):
                    # It's a directory, continue recursion
                    add_nodes(value, current_path, current_path)
        
        add_nodes(self.file_structure)
        
        # Use a custom hierarchical layout instead of graphviz
        pos = self._custom_hierarchical_layout(G)
        
        plt.figure(figsize=(15, 10))
        # Draw nodes
        nx.draw_networkx_nodes(G, pos, node_size=1000, node_color="skyblue")
        
        # Draw edges
        nx.draw_networkx_edges(G, pos, arrows=False)
        
        # Draw labels
        labels = {node: G.nodes[node].get('label', os.path.basename(node)) for node in G.nodes()}
        nx.draw_networkx_labels(G, pos, labels=labels, font_size=8, font_weight="bold")
        
        plt.axis('off')
        plt.savefig(output_file, bbox_inches='tight')
        plt.close()
        print(f"Structure visualization saved to {output_file}")
        
    def _custom_hierarchical_layout(self, G):
        """Create a custom hierarchical layout for the graph"""
        # Identify root nodes (no incoming edges)
        root_nodes = [n for n in G.nodes() if G.in_degree(n) == 0]
        
        # Calculate positions
        pos = {}
        max_depth = 0
        node_widths = defaultdict(int)
        
        # First pass: calculate depths and widths
        def calculate_metrics(node, depth=0):
            nonlocal max_depth
            max_depth = max(max_depth, depth)
            
            children = list(G.successors(node))
            if not children:
                node_widths[depth] += 1
                return 1
                
            width = 0
            for child in children:
                width += calculate_metrics(child, depth + 1)
                
            node_widths[depth] += 1
            return width
            
        total_width = 0
        for root in root_nodes:
            total_width += calculate_metrics(root)
            
        # Second pass: assign positions
        width_used = defaultdict(int)
        
        def assign_positions(node, depth=0, x_offset=0):
            children = list(G.successors(node))
            
            # Position for this node
            x_pos = x_offset + width_used[depth]
            width_used[depth] += 1
            pos[node] = (x_pos, -depth)  # Negative to go top-down
            
            # Position children
            if children:
                for child in children:
                    assign_positions(child, depth + 1, x_offset)
                    
        for root in root_nodes:
            assign_positions(root)
            
        return pos
        
    def visualize_dependencies(self, output_file="dependencies.png"):
        """Visualize dependencies between files"""
        G = nx.DiGraph()
        
        # Build dependency graph from file structure
        def extract_dependencies(structure, path=""):
            for key, value in structure.items():
                current_path = os.path.join(path, key)
                
                # Check if it's a file with dependencies
                if isinstance(value, dict) and "dependencies" in value:
                    G.add_node(current_path)
                    for dep in value["dependencies"]:
                        # Skip special Terraform dependencies for visualization clarity
                        if dep.startswith('module:') or dep.startswith('resource:') or dep.startswith('data:') or dep.startswith('var:'):
                            continue
                        
                        # Use the resolved absolute path
                        if os.path.exists(dep):
                            G.add_node(dep)
                            G.add_edge(current_path, dep)
                
                # Recurse into directories
                elif isinstance(value, dict) and any(isinstance(value[k], dict) for k in value.keys()):
                    extract_dependencies(value, current_path)
        
        extract_dependencies(self.file_structure)
        
        if len(G) > 50:  # If too many nodes, skip visualization
            print("Too many dependencies to visualize clearly.")
            return
            
        if len(G) == 0:  # No dependencies to visualize
            print("No dependencies found to visualize.")
            return
            
        plt.figure(figsize=(15, 10))
        
        # Use force-directed layout
        pos = nx.spring_layout(G, k=0.5, iterations=100, seed=42)
        
        # Draw nodes and edges
        nx.draw_networkx_nodes(G, pos, node_size=500, node_color="lightgreen")
        nx.draw_networkx_edges(G, pos, arrows=True, arrowsize=10, width=0.5)
        
        # Create better labels using just filenames
        labels = {node: os.path.basename(node) for node in G.nodes()}
        nx.draw_networkx_labels(G, pos, labels=labels, font_size=8)
        
        plt.axis('off')
        plt.savefig(output_file, bbox_inches='tight')
        plt.close()
        print(f"Dependency visualization saved to {output_file}")
        
    def _resolve_absolute_import(self, source_file, import_name):
        """Resolve an import to an absolute file path"""
        # Normalize source file path 
        source_file = os.path.normpath(os.path.join(self.local_path, source_file))
        source_dir = os.path.dirname(source_file)
        
        # Replace dots with directory separators
        relative_path = import_name.replace('.', os.sep)
        
        # Check common file extensions
        possible_extensions = ['.py', '.js', '.tsx', '.jsx', '.ts', '.java', '.go', '.tf']
        
        # Search strategies for resolution
        search_paths = [
            # 1. First try the direct path from the source directory
            os.path.join(source_dir, relative_path),
            # 2. Try from the root of the project
            os.path.join(self.local_path, relative_path)
        ]
        
        for base_path in search_paths:
            for ext in possible_extensions:
                # Direct file import
                potential_path = base_path + ext
                if os.path.exists(potential_path):
                    return os.path.normpath(potential_path)
                
                # Package import (check for __init__.py or index.js)
                if ext in ['.py', '.js']:
                    index_file = '__init__.py' if ext == '.py' else 'index.js'
                    package_path = os.path.join(base_path, index_file)
                    if os.path.exists(package_path):
                        return os.path.normpath(package_path)
        
        # Terraform module resolution
        if import_name.startswith('.'):
            # Relative module
            potential_path = os.path.normpath(os.path.join(source_dir, import_name))
            if os.path.exists(potential_path):
                return potential_path
        
        return None
        
    def export_summary(self, output_file="repo_json_summary.json"):
        """Export the repository summary to a JSON file"""
        summary = self.generate_summary()
        
        with open(output_file, 'w') as f:
            json.dump(summary, f, indent=2)
            
        print(f"Repository summary exported to {output_file}")
        
    def print_summary(self):
        """Print a summary of the repository to the console"""
        summary = self.generate_summary()
        
        # Create output string to save to file
        output = []
        output.append("\n=== Repository Summary ===")
        output.append(f"Total files: {summary['file_count']}")
        output.append(f"Total directories: {summary['directory_count']}")
        output.append("\nFile types:")
        for ext, count in sorted(summary['file_types'].items(), key=lambda x: x[1], reverse=True):
            output.append(f"  {ext}: {count}")
            
        output.append("\nTop-level structure:")
        
        # Helper function to build structure string
        def build_structure_string(structure, depth=4, max_depth=None, indent="  "):
            if max_depth is not None and depth > max_depth:
                return [f"{indent * depth}..."]
                
            structure_lines = []
            for key, value in sorted(structure.items()):
                if isinstance(value, dict) and not any(isinstance(value[k], dict) for k in value.keys() if k != "dependencies"):
                    dep_count = len(value.get("dependencies", [])) if "dependencies" in value else 0
                    if dep_count > 0:
                        structure_lines.append(f"{indent * depth}F {key} [{dep_count} deps]")
                    else:
                        structure_lines.append(f"{indent * depth}F {key}")
                else:
                    structure_lines.append(f"{indent * depth}D {key}/")
                    if max_depth is None or depth < max_depth:
                        structure_lines.extend(build_structure_string(value, depth + 1, max_depth, indent))
            return structure_lines
            
        output.extend(build_structure_string(self.file_structure, depth=4, max_depth=6))
        
        output.append("\nMost connected files (with most dependencies):")
        # Collect files with dependencies from the structure
        files_with_deps = []
        
        def collect_deps(structure, path=""):
            for key, value in structure.items():
                current_path = os.path.join(path, key)
                
                if isinstance(value, dict) and "dependencies" in value:
                    files_with_deps.append((current_path, len(value["dependencies"])))
                
                elif isinstance(value, dict) and any(isinstance(value[k], dict) for k in value.keys()):
                    collect_deps(value, current_path)
        
        collect_deps(self.file_structure)
        
        # Sort and display top files
        top_files = sorted(files_with_deps, key=lambda x: x[1], reverse=True)[:5]
        for file, dep_count in top_files:
            output.append(f"  {file}: {dep_count} dependencies")
            
        # Add Terraform-specific summary if applicable
        if '.tf' in summary['file_types']:
            output.extend(self._get_terraform_summary())
            
        # Write output to file
        with open('repo_print_summary.txt', 'w') as f:
            f.write('\n'.join(output))
            
    def _get_terraform_summary(self):
        """Get Terraform-specific summary information as list of strings"""
        output = []
        output.append("\n=== Terraform Summary ===")
        
        modules = {}
        resources = {}
        data_sources = {}
        variables = set()
        
        # Collect Terraform components from the file structure
        def collect_terraform_deps(structure, path=""):
            for key, value in structure.items():
                current_path = os.path.join(path, key)
                
                if isinstance(value, dict) and "dependencies" in value:
                    for dep in value["dependencies"]:
                        if dep.startswith('module:'):
                            _, module_name, module_source = dep.split(':', 2)
                            modules[module_name] = module_source
                        elif dep.startswith('resource:'):
                            _, resource_type, resource_name = dep.split(':', 2)
                            if resource_type not in resources:
                                resources[resource_type] = []
                            resources[resource_type].append(resource_name)
                        elif dep.startswith('data:'):
                            _, data_type, data_name = dep.split(':', 2)
                            if data_type not in data_sources:
                                data_sources[data_type] = []
                            data_sources[data_type].append(data_name)
                        elif dep.startswith('var:'):
                            variables.add(dep.split(':', 1)[1])
                
                elif isinstance(value, dict) and any(isinstance(value[k], dict) for k in value.keys()):
                    collect_terraform_deps(value, current_path)
        
        collect_terraform_deps(self.file_structure)
        
        # Add modules
        if modules:
            output.append("\nModules:")
            for name, source in modules.items():
                output.append(f"  {name}: {source}")
                
        # Add resources
        if resources:
            output.append("\nResources:")
            for type_name, names in resources.items():
                output.append(f"  {type_name}: {len(names)} resources")
                
        # Add data sources
        if data_sources:
            output.append("\nData Sources:")
            for type_name, names in data_sources.items():
                output.append(f"  {type_name}: {len(names)} instances")
                
        # Add variables
        if variables:
            output.append(f"\nVariables Referenced: {len(variables)}")
            if len(variables) <= 10:  # Only print if not too many
                for var in sorted(variables):
                    output.append(f"  var.{var}")
                    
        return output
            
    def _print_structure(self, structure, depth=0, max_depth=None, indent="  "):
        """Build file structure string recursively up to max_depth"""
        if max_depth is not None and depth > max_depth:
            return [f"{indent * depth}..."]
            
        output = []
        for key, value in sorted(structure.items()):
            if isinstance(value, dict) and not any(isinstance(value[k], dict) for k in value.keys() if k != "dependencies"):
                dep_count = len(value.get("dependencies", [])) if "dependencies" in value else 0
                if dep_count > 0:
                    output.append(f"{indent * depth}📄 {key} [{dep_count} deps]")
                else:
                    output.append(f"{indent * depth}📄 {key}")
            else:
                output.append(f"{indent * depth}📁 {key}/")
                if max_depth is None or depth < max_depth:
                    output.extend(self._print_structure(value, depth + 1, max_depth, indent))
        return output


def main():
    parser = argparse.ArgumentParser(description="Analyze a GitHub repository's structure and dependencies")
    parser.add_argument("--url", help="GitHub repository URL to analyze")
    parser.add_argument("--path", help="Path to local repository")
    parser.add_argument("--output", default="repo_json_summary.json", help="Output file for the summary")
    parser.add_argument("--visualize", action="store_true", help="Generate visualizations")
    
    args = parser.parse_args()
    
    if not args.url and not args.path:
        parser.error("Either --url or --path must be provided")
        
    analyzer = GitHubRepoAnalyzer(repo_url=args.url, local_path=args.path)
    
    if args.url and not args.path:
        if not analyzer.clone_repo():
            return
            
    if analyzer.analyze_repo():
        analyzer.print_summary()
        analyzer.export_summary(args.output)
        
        if args.visualize:
            analyzer.visualize_structure()
            analyzer.visualize_dependencies()


if __name__ == "__main__":
    main()