from swarm import Swarm, Agent
import json

# dependencies in the examples should have root dependencies added to the dependencies list

# main.tf to be considered from root if root is mentioned

class Codebase:
    def __init__(self, repo_json_summary, repo_print_summary, repo_root_dir):
        # Read repo print summary text file
        with open(repo_print_summary, 'r') as f:
            self.repo_print_summary = f.read()
            
        # Read repo json summary file
        with open(repo_json_summary, 'r') as f:
            self.repo_json_summary = json.load(f)

        self.repo_root_dir = repo_root_dir
        self.client = Swarm()
        self.coder_agent = Agent(
            name="Coder Agent",
            instructions=f"""
                You are a Terraform code assistant. Your task is to analyze code change requests and implement them correctly.

                Important file path handling rules:
                1. All file paths must be prefixed with "{self.repo_root_dir}/"
                2. Always use forward slashes (/) in paths, even on Windows
                3. The repository root directory is: {self.repo_root_dir}
                4. All paths in get_code_context() must be absolute paths starting from {self.repo_root_dir}

                Follow these steps for each request:
                1. Analyze the request to identify which files need modification
                2. Use the repository structure in repo_json_summary to locate the exact files
                3. Construct the full file path by joining {self.repo_root_dir} with the relative path
                4. Use get_code_context() with the FULL path to read current code
                5. Make the requested changes while preserving the overall structure

                Example output format:
                File: {self.repo_root_dir}/path/to/file.tf
                ```
                # Modified code here
                ```

                Available tools:
                - get_code_context(file_path): Reads file content. MUST use full path from {self.repo_root_dir}
                - Repository structure in repo_json_summary 
                - Overall context in repo_print_summary

                Focus on:
                1. Always using complete paths starting with {self.repo_root_dir}
                2. Making precise, targeted changes
                3. Maintaining existing code patterns
            """,
            model="gpt-4o"
        )
        self.coder_agent.functions.append(self.get_code_context)

    def get_code_context(self, file_path):
        """Get code from files for context.
            
        This function is used by the code agent to read code from dependency files
        to better understand the codebase context. By reading related files, the agent
        can write more informed and contextually appropriate code.
        
        Args:
            file_path (str): Absolute path to the file
            
        Returns:
            str: The extracted code from the file
        """
        print(f"Getting code context for file: {file_path}")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                code = ''.join(lines)
                
            return code
            
        except FileNotFoundError:
            print(f"Error: File {file_path} not found")
            return f"Error: File {file_path} not found"
        except Exception as e:
            print(f"Error reading file: {str(e)}")
            return f"Error reading file: {str(e)}"

def main():
    # Update the region in the simple example from eu-west-1 to asia-south-1
    # Update the vpc_cidr in the outpost example to 10.0.0.0/22
    codebase = Codebase("repo_json_summary.json","repo_print_summary.txt", "terraform-aws-vpc")
    messages = [{"role": "user", "content": "Update the vpc_cidr in the outpost example to 10.0.0.0/22"}]
    response = codebase.client.run(agent=codebase.coder_agent, messages=messages)
    print(response.messages[-1]["content"])

if __name__ == "__main__":
    main()
