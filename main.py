import streamlit as st
import openai
import subprocess
import os
from git import Repo
from github_repo_summarizer import GitHubRepoAnalyzer
from agents.core import Codebase

# Initialize session state for chat history if it doesn't exist
if "messages" not in st.session_state:
    st.session_state.messages = []

st.title("Opsly Demo")

# Add GitHub repo cloning section
repo_url = "https://github.com/terraform-aws-modules/terraform-aws-vpc.git"
if st.button("Clone Repository & Summarize"):
    if repo_url:
        try:
            if os.path.exists("terraform-aws-vpc"):
                if os.path.isdir("terraform-aws-vpc"):
                    import shutil
                    shutil.rmtree("terraform-aws-vpc")
                else:
                    os.remove("terraform-aws-vpc")
            Repo.clone_from(repo_url, "terraform-aws-vpc")
            st.success("Repository Cloned")
            analyzer = GitHubRepoAnalyzer(local_path="terraform-aws-vpc")
            
            if analyzer.analyze_repo():
                analyzer.print_summary()
                analyzer.export_summary()
                st.success("Repository Summarized")
        except Exception as e:
            st.error(f"Failed to clone repository: {e}, Repo already exists")
    else:
        st.warning("Please enter a GitHub repository URL")

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Get user input
if prompt := st.chat_input("What modifications would you like to make to the VPC?"):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Get OpenAI response
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        # Generate OpenAI response
        codebase = Codebase("repo_json_summary.json","repo_print_summary.txt", "terraform-aws-vpc")
        response = codebase.client.run(agent=codebase.coder_agent, messages=st.session_state.messages)
        full_response = response.messages[-1]["content"]
        message_placeholder.markdown(full_response)
    
    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": full_response})
