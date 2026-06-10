import os
import io
import zipfile
import logging
import tempfile
import pandas as pd
import streamlit as st
import plotly.express as px
from dotenv import load_dotenv
from typing import Optional, Dict
from agilemind.utils import ModelLibrary
from agilemind.agile import dev as agile_dev
from contextlib import contextmanager, redirect_stdout, redirect_stderr


class ApplicationLogFilter(logging.Filter):
    """Filter to only show logs from agilemind modules and direct prints."""

    def __init__(self):
        super().__init__()
        self.allowed_modules = ["codeagent"]

    def filter(self, record):
        # Always allow direct print statements
        if not hasattr(record, "name") or record.name == "root":
            return True

        # Only allow logs from agilemind modules
        return any(record.name.startswith(module) for module in self.allowed_modules)


class StreamToLogger:
    """Redirect stdout/stderr to a logger."""

    def __init__(self, logger, log_level=logging.INFO):
        self.logger = logger
        self.log_level = log_level
        self.linebuf = ""

    def write(self, buf):
        for line in buf.rstrip().splitlines():
            self.logger.log(self.log_level, line.rstrip())

    def flush(self):
        pass


class WebLogHandler(logging.Handler):
    """Custom log handler to capture logs in Streamlit session state."""

    def __init__(self, container):
        super().__init__()
        self.container = container
        self.log_output = []
        self.log_area = self.container.empty()
        self.setFormatter(logging.Formatter("%(message)s"))

    def emit(self, record):
        try:
            log_entry = self.format(record)
            if "logs" not in st.session_state:
                st.session_state.logs = []
            st.session_state.logs.append(log_entry)

            # Keep only the latest logs to avoid performance issues
            if len(st.session_state.logs) > 1000:
                st.session_state.logs = st.session_state.logs[-1000:]

            # Update display with all logs
            self.log_output.append(log_entry)
            self.log_area.code(
                "\n".join(self.log_output),
                language=None,
                line_numbers=True,
                wrap_lines=True,
                height=350,
            )
        except Exception as e:
            # In case of error, try a simple approach
            self.log_area.write(f"Log error: {str(e)}")

    def clear(self):
        self.log_output = []
        self.log_area.empty()
        if "logs" in st.session_state:
            st.session_state.logs = []


def setup_logging():
    """Set up logging to capture both Python logs and stdout/stderr."""
    # Create a container for logs
    log_container = st.container()

    # Create and configure our custom handler
    handler = WebLogHandler(log_container)
    handler.setLevel(logging.INFO)

    # Add a filter to only show application logs
    app_filter = ApplicationLogFilter()
    handler.addFilter(app_filter)

    # Get the root logger and configure it
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Remove any existing handlers to avoid duplication
    for h in root_logger.handlers[:]:
        root_logger.removeHandler(h)

    # Add our custom handler
    root_logger.addHandler(handler)

    # Redirect stdout and stderr to our logger
    stdout_logger = StreamToLogger(root_logger, logging.INFO)
    stderr_logger = StreamToLogger(root_logger, logging.ERROR)

    # Return the handler so we can clear logs later
    return handler, stdout_logger, stderr_logger


@contextmanager
def setup_environment(api_key: str, api_base_url: Optional[str] = None):
    """Set up environment variables for the development process."""
    # Create a temporary .env file
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".env") as env_file:
        env_file.write(f'OPENAI_API_KEY="{api_key}"\n')
        if api_base_url:
            env_file.write(f'OPENAI_BASE_URL="{api_base_url}"\n')

        # Store the path to delete it later
        st.session_state.env_file_path = env_file.name

    # Load environment variables from the temporary file
    load_dotenv(env_file.name)

    try:
        yield
    finally:
        # Clean up: remove the temporary .env file
        if st.session_state.env_file_path and os.path.exists(
            st.session_state.env_file_path
        ):
            os.unlink(st.session_state.env_file_path)
            st.session_state.env_file_path = None


def create_zip_from_directory(directory_path: str) -> bytes:
    """Create a ZIP file from the directory."""
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(directory_path):
            # Skip pycache directories
            if "pycache" in root:
                continue
            for file in files:
                # Skip pycache related files
                if "pycache" in file or file.endswith(".pyc"):
                    continue
                file_path = os.path.join(root, file)
                zipf.write(file_path, os.path.relpath(file_path, directory_path))
    memory_file.seek(0)
    return memory_file.getvalue()


def scan_directory(directory_path: str) -> Dict[str, str]:
    """Scan a directory and return files with their contents."""
    files_dict = {}
    for root, _, files in os.walk(directory_path):
        if "pycache" in root:
            continue
        for file in files:
            if "pycache" in file or file.endswith(".pyc"):
                continue
            file_path = os.path.join(root, file)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    relative_path = os.path.relpath(file_path, directory_path)
                    files_dict[relative_path] = f.read()
            except UnicodeDecodeError:
                relative_path = os.path.relpath(file_path, directory_path)
                files_dict[relative_path] = "(Binary file)"
    return files_dict


def display_file_structure(files: Dict[str, str]):
    """Display file structure as a tree and allow viewing file content."""
    file_paths = list(files.keys())
    file_paths.sort()
    directories = {}
    root_files = []

    for file_path in file_paths:
        parts = file_path.split("/")
        if len(parts) > 1:
            dir_path = "/".join(parts[:-1])
            if dir_path not in directories:
                directories[dir_path] = []
            directories[dir_path].append(file_path)
        else:
            root_files.append(file_path)

    dir_names = sorted(list(directories.keys()))

    tab_names = dir_names.copy()
    if root_files:
        tab_names = ["root"] + tab_names

    if tab_names:
        tabs = st.tabs(tab_names)

        # Index to track which tab we're on
        tab_index = 0

        # Handle root files if any
        if root_files:
            with tabs[tab_index]:
                st.caption("Files in root directory")
                for file_path in sorted(root_files):
                    display_file(file_path, files[file_path])
            tab_index += 1

        # Handle directories
        for dir_name in dir_names:
            with tabs[tab_index]:
                st.caption(f"Files in {dir_name}/")
                for file_path in sorted(directories[dir_name]):
                    display_file(file_path, files[file_path])
            tab_index += 1


def display_file(file_path: str, content: str):
    """Display a file with expandable content."""
    # Determine language for syntax highlighting
    extension = file_path.split(".")[-1].lower() if "." in file_path else ""
    language_map = {
        "py": "python",
        "js": "javascript",
        "html": "html",
        "css": "css",
        "md": "markdown",
        "json": "json",
        "txt": "text",
    }
    language = language_map.get(extension, "text")

    with st.expander(file_path):
        if content == "(Binary file)":
            st.write("Binary file, preview not available")
        else:
            st.code(content, language=language, line_numbers=True)


def start_development_process(
    demand: str,
    model: str,
    output_dir: str,
    api_key: str,
    api_base_url: str,
    uploaded_file: Optional[io.BytesIO] = None,
    max_iterations: int = 5,
):
    """Actual development process execution after UI update."""
    # Set up logging before starting the process
    log_handler, stdout_redirect, stderr_redirect = setup_logging()

    with setup_environment(api_key, api_base_url):
        try:
            # Redirect stdout/stderr to our logger during development
            with redirect_stdout(stdout_redirect), redirect_stderr(stderr_redirect):
                logging.info("Starting development process...")
                logging.info(f"Demand: {demand}")
                logging.info(f"Model: {model}")
                logging.info(f"Output directory: {output_dir}")

                # Handle the uploaded file if present
                file_path = None
                if uploaded_file is not None:
                    # Create a temp file to store the uploaded content
                    temp_file = tempfile.NamedTemporaryFile(
                        delete=False, suffix=os.path.splitext(uploaded_file.name)[1]
                    )
                    temp_file.write(uploaded_file.getvalue())
                    temp_file.close()
                    file_path = temp_file.name
                    logging.info(
                        f"Using uploaded file: {uploaded_file.name} (saved as {file_path})"
                    )

                result = agile_dev(
                    demand=demand,
                    output=output_dir,
                    model=model,
                    file=file_path,  # Pass the file path to agile_dev
                    max_iterations=max_iterations,
                    interactive=False,
                )

                # Clean up the temp file after development is complete
                if file_path and os.path.exists(file_path):
                    try:
                        os.unlink(file_path)
                    except Exception as e:
                        logging.warning(
                            f"Failed to delete temporary file {file_path}: {e}"
                        )

            st.session_state.output_dir = output_dir
            st.session_state.generated_files = scan_directory(output_dir)
            st.session_state.development_stats = result

        except Exception as e:
            logging.error(f"Error during development: {str(e)}")
            st.exception(e)
        finally:
            st.toast("Development process completed")
            st.session_state.development_complete = True
            st.session_state.development_in_progress = False
            st.rerun()


def display_development_stats():
    """Display statistics about the development process."""
    stats = st.session_state.development_stats

    # Check if stats has required data
    if not stats or not isinstance(stats, dict):
        st.header("⚠️ Development Statistics Unavailable")
        st.warning(
            "Development statistics not available.\n\n"
            "This could be due to an error during the development process or "
            "the process not being completed successfully.\n\n"
            "Please try again or check the logs for more information."
        )
        return

    # Extract data from stats
    token_usage = stats.get("token_usage", {})
    cost_data = stats.get("cost", {})
    used_tools = stats.get("used_tools", [])

    st.header("Development Process Overview")
    st.info(
        "The web platform does not support interactive development and parallelization yet. "
        "The time usage may be more than expected."
    )

    tab0, tab1, tab2, tab3, tab4, tab5 = st.tabs(
        [
            "Summary",
            "Files",
            "Token Usage",
            "API Calls",
            "Cost Analysis",
            "Development Timeline",
        ]
    )
    with tab0:
        st.subheader("Development Results")
        col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
        with col1:
            st.subheader("Time")
            started_at = stats.get("started_at", "")
            finished_at = stats.get("finished_at", "")

            if started_at and finished_at:
                start_dt = pd.to_datetime(started_at)
                finish_dt = pd.to_datetime(finished_at)
                elapsed_time = finish_dt - start_dt

                st.metric("Start", started_at)
                st.metric("Finish", finished_at)
                st.metric("Elapsed", f"{elapsed_time.total_seconds() / 60:.2f} min")
            else:
                st.warning("Time information not available")

        with col2:
            st.subheader("Token")
            prompt_tokens = token_usage.get("total", {}).get("prompt_tokens", 0)
            completion_tokens = token_usage.get("total", {}).get("completion_tokens", 0)
            total_token_count = token_usage.get("total", {}).get("total_tokens", 0)
            st.metric("Prompt Tokens", f"{prompt_tokens:,}")
            st.metric("Completion Tokens", f"{completion_tokens:,}")
            st.metric("Total Tokens", f"{total_token_count:,}")

        with col3:
            st.subheader("Cost")
            prompt_cost = cost_data.get("total", {}).get("prompt_cost", 0.0)
            completion_cost = cost_data.get("total", {}).get("completion_cost", 0.0)
            total_cost = cost_data.get("total", {}).get("total_cost", 0.0)
            st.metric("Prompt Cost", f"${prompt_cost:.4f}")
            st.metric("Completion Cost", f"${completion_cost:.4f}")
            st.metric("Total Cost", f"${total_cost:.4f}")

        with col4:
            st.subheader("Files")
            files = st.session_state.generated_files
            code_files = [
                f for f in files if f.endswith((".py", ".js", ".html", ".css"))
            ]
            doc_files = [f for f in files if f.endswith((".md", ".txt", ".json"))]
            st.metric("Code Files", len(code_files))
            st.metric("Line Count", sum(len(files[f].splitlines()) for f in code_files))
            st.metric("Doc Files", len(doc_files))

    with tab1:
        # Display file structure
        st.header("Project Files")
        # Offer download
        if st.session_state.output_dir and os.path.exists(st.session_state.output_dir):
            zip_data = create_zip_from_directory(st.session_state.output_dir)
            st.download_button(
                label="Download Project as ZIP",
                data=zip_data,
                file_name="codeagent_project.zip",
                mime="application/zip",
                help="Download the complete project as a ZIP file",
                icon="📦",
            )
        if st.session_state.generated_files:
            display_file_structure(st.session_state.generated_files)
        else:
            st.warning("No files were generated.")

    with tab2:
        # Process token usage by agent data
        agent_data = token_usage.get("by_agent", {})
        if agent_data:
            agent_df = pd.DataFrame(
                [
                    {
                        "Agent": agent,
                        "Prompt Tokens": data.get("prompt_tokens", 0),
                        "Completion Tokens": data.get("completion_tokens", 0),
                    }
                    for agent, data in agent_data.items()
                ]
            )

            with st.container():
                fig = px.pie(
                    agent_df,
                    values="Prompt Tokens",
                    names="Agent",
                    title="Token Usage by Agent",
                    hover_data=["Completion Tokens"],
                    labels={"Prompt Tokens": "Prompt Tokens"},
                )
                st.plotly_chart(fig, use_container_width=True)

            with st.container():
                # Display detailed token usage table
                agent_df = agent_df.sort_values("Prompt Tokens", ascending=False)
                agent_df["Total Tokens"] = (
                    agent_df["Prompt Tokens"] + agent_df["Completion Tokens"]
                )

                # Ensure all token columns are numeric type
                for col in ["Prompt Tokens", "Completion Tokens", "Total Tokens"]:
                    # Convert any string representations with commas to numeric
                    agent_df[col] = pd.to_numeric(
                        agent_df[col].astype(str).str.replace(",", ""),
                        errors="coerce",
                    )

                agent_df = agent_df.rename(
                    columns={
                        "Prompt Tokens": "Prompt Tokens",
                        "Completion Tokens": "Completion Tokens",
                        "Total Tokens": "Total Tokens",
                    }
                )
                st.dataframe(
                    agent_df.style.background_gradient(
                        subset=["Total Tokens"], cmap="Blues"
                    ),
                    use_container_width=True,
                )

    with tab3:
        # Process detailed API call data
        detailed_data = token_usage.get("detailed", [])
        if detailed_data:
            calls_df = pd.DataFrame(detailed_data)
            if not calls_df.empty:
                if "timestamp" in calls_df.columns:
                    calls_df["timestamp"] = pd.to_datetime(calls_df["timestamp"])
                    calls_df["formatted_time"] = calls_df["timestamp"].dt.strftime(
                        "%H:%M:%S"
                    )

                st.dataframe(
                    calls_df[
                        [
                            "agent",
                            "round",
                            "model",
                            "prompt_tokens",
                            "completion_tokens",
                            "total_tokens",
                            "formatted_time",
                        ]
                    ]
                    .rename(
                        columns={
                            "agent": "Agent",
                            "round": "Round",
                            "model": "Model",
                            "prompt_tokens": "Prompt Tokens",
                            "completion_tokens": "Completion Tokens",
                            "total_tokens": "Total Tokens",
                            "formatted_time": "Time",
                        }
                    )
                    .style.background_gradient(subset=["Total Tokens"], cmap="Blues")
                )

                # Completion-to-prompt ratio
                total_prompt = calls_df["prompt_tokens"].sum()
                total_completion = calls_df["completion_tokens"].sum()
                if total_prompt > 0:
                    ratio = total_completion / total_prompt
                    st.metric("Completion-to-Prompt Ratio", f"{ratio:.2f}")

    with tab4:
        agent_cost_data = cost_data.get("by_agent", {})
        if agent_cost_data:
            cost_df = pd.DataFrame(
                [
                    {
                        "Agent": agent,
                        "Prompt Cost": data.get("prompt_cost", 0),
                        "Completion Cost": data.get("completion_cost", 0),
                        "Total Cost": data.get("total_cost", 0),
                    }
                    for agent, data in agent_cost_data.items()
                ]
            )

            cost_df = cost_df.sort_values("Total Cost", ascending=False)

            # Create pie chart for cost distribution
            fig = px.pie(
                cost_df,
                values="Total Cost",
                names="Agent",
                title="Cost Distribution by Agent",
                hover_data=["Prompt Cost", "Completion Cost"],
                labels={"Total Cost": "Total Cost ($)"},
            )
            st.plotly_chart(fig, use_container_width=True)

            # Display detailed cost table
            with st.expander("View Cost Details"):
                # Format currency columns to display as $
                for col in ["Prompt Cost", "Completion Cost", "Total Cost"]:
                    cost_df[col] = cost_df[col].map("${:.4f}".format)
                st.dataframe(cost_df)

    with tab5:
        history_data = stats.get("history", [])
        if history_data:
            # Convert to DataFrame
            history_df = pd.DataFrame(
                [
                    {
                        "Step": item.get("step", "Unknown"),
                        "Time": item.get("time", ""),
                    }
                    for item in history_data
                ]
            )

            # Format time
            if not history_df.empty and "Time" in history_df.columns:
                history_df["Time"] = pd.to_datetime(history_df["Time"])
                history_df = history_df.sort_values("Time")

                # Calculate durations
                history_df["Duration"] = (
                    history_df["Time"].diff().fillna(pd.Timedelta(seconds=0))
                )
                history_df["Duration (s)"] = history_df["Duration"].dt.total_seconds()
                history_df["End Time"] = history_df["Time"].shift(-1)

                # Use the actual finished_at time for the last item
                if "finished_at" in stats:
                    finish_time = pd.to_datetime(stats["finished_at"])
                    history_df.iloc[-1, history_df.columns.get_loc("End Time")] = (
                        finish_time
                    )
                else:
                    history_df.iloc[
                        -1, history_df.columns.get_loc("End Time")
                    ] = history_df["Time"].iloc[-1] + pd.Timedelta(
                        seconds=30
                    )  # Fallback with a small buffer

                # Create Gantt chart
                fig = px.timeline(
                    history_df,
                    x_start="Time",
                    x_end="End Time",
                    y="Step",
                    color="Step",
                    title="Development Process Timeline",
                )
                fig.update_layout(xaxis_title="Time", yaxis_title="")
                st.plotly_chart(fig, use_container_width=True)

                # Display steps table
                with st.expander("View Development Steps"):
                    # Format for display
                    display_df = history_df.copy()
                    display_df["Time"] = display_df["Time"].dt.strftime("%H:%M:%S")
                    display_df["Duration"] = display_df["Duration"].apply(
                        lambda x: f"{x.total_seconds():.2f}s"
                    )
                    st.dataframe(
                        display_df[
                            ["Step", "Time", "Duration"]
                        ].style.background_gradient(cmap="Greens")
                    )


# -------------------------------------------
# -------------- Streamlit App --------------
# -------------------------------------------

# Set page config
st.set_page_config(
    page_title="CodeAgent - Complex code generation Agent",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# State management
if "output_dir" not in st.session_state:
    st.session_state.output_dir = None
if "generated_files" not in st.session_state:
    st.session_state.generated_files = {}
if "development_complete" not in st.session_state:
    st.session_state.development_complete = False
if "development_in_progress" not in st.session_state:
    st.session_state.development_in_progress = False
if "env_file_path" not in st.session_state:
    st.session_state.env_file_path = None
if "development_stats" not in st.session_state:
    st.session_state.development_stats = {}
if "logs" not in st.session_state:
    st.session_state.logs = []

if (
    not st.session_state.development_complete
    and not st.session_state.development_in_progress
):
    st.title("CodeAgent")
    st.caption("Complex code generation Agent")


with st.sidebar:
    st.title("CodeAgent")

    if st.button("New Project", use_container_width=True):
        st.session_state.development_complete = False
        st.session_state.development_in_progress = False
        st.session_state.logs = []
        st.session_state.generated_files = {}
        st.session_state.development_stats = {}
        st.session_state.output_dir = None
        st.session_state.env_file_path = None
        st.rerun()

    st.markdown("---")
    st.header("Configuration")

    # API credentials
    st.subheader("API Credentials")
    api_key = st.text_input(
        "OpenAI API Key", type="password", help="Your OpenAI API key"
    )
    api_base_url = st.text_input(
        "API Base URL (Optional)",
        type="password",
        value="https://api.openai.com/v1",
        help="Custom API endpoint URL (if using a proxy)",
    )

    # Model selection
    st.subheader("Model Selection")
    model = st.selectbox(
        "Select Model",
        options=ModelLibrary.get_known_model_names(),
        help="Choose the LLM to use",
    )

    st.subheader("Advanced Settings")
    # Advanced settings as a collapsible drawer
    with st.expander("Click to expand", expanded=False):
        max_iterations = st.slider(
            "Max Iterations",
            min_value=1,
            max_value=10,
            value=5,
            help="Maximum number of development iterations",
        )

        # Output directory
        output_dir = st.text_input(
            "Output Directory",
            value=tempfile.mkdtemp(prefix="codeagent_output_"),
            help="Directory where the generated project will be saved",
            disabled=True,
        )


# Main content area
if st.session_state.development_complete:
    display_development_stats()


elif st.session_state.development_in_progress:
    st.header("Development in Progress")
    st.info(
        "The web platform does not support interactive development and parallelization yet. "
        "The time usage may be more than expected."
    )
    st.markdown("---")

    # Create log display area before starting the development process
    log_display = st.container()
    with log_display:
        st.subheader("Development Logs")

    start_development_process(
        demand=st.session_state.demand,
        model=model,
        output_dir=output_dir,
        api_key=api_key,
        api_base_url=api_base_url,
        uploaded_file=(
            st.session_state.uploaded_file
            if "uploaded_file" in st.session_state
            else None
        ),
        max_iterations=max_iterations,
    )

else:
    st.write("\n" * 3)
    st.subheader("Project Specification")

    with st.form("project_form"):
        demand = st.text_area(
            "Describe the software you want to build",
            height=150,
            help="Provide a detailed description of what you want CodeAgent to build",
            value="Create a 2048 game with a modern UI, keyboard controls, and score tracking.",
        )

        # Add file uploader component
        uploaded_file = st.file_uploader(
            "Upload a file (optional)",
            help="Upload a file to be used in the development process",
            type=None,  # Allow all file types
        )

        if st.form_submit_button("Start Development"):
            if not api_key:
                st.error("Please provide an API key")
            elif not demand:
                st.error("Please describe the software you want to build")
            else:
                st.session_state.demand = demand
                if uploaded_file is not None:
                    st.session_state.uploaded_file = uploaded_file
                st.session_state.development_in_progress = True
                st.session_state.development_complete = False
                st.rerun()
