"""
CLI window display using rich to show live updates.
"""

import uuid
import time
import threading
from rich import box
from rich.live import Live
from rich.text import Text
from rich.rule import Rule
from rich.tree import Tree
from rich.table import Table
from rich.panel import Panel
from datetime import datetime
from rich.console import Group
from rich.console import Console
from typing import Any, Dict, Optional, Literal, List, Tuple, Callable

SPINNER = ["|", "/", "-", "\\"]


def intercept_print(log_window: "LogWindow", level: str = "INFO") -> Callable:
    """
    Intercept the built-in print function and redirect output to the LogWindow.

    Args:
        log_window: The LogWindow instance to send print output to
        level: Log level to use for the intercepted print messages

    Returns:
        A function to restore the original print function
    """
    import builtins

    original_print = builtins.print

    def custom_print(*args, **kwargs):
        # Extract file and sep kwargs if provided
        file = kwargs.get("file", None)
        sep = kwargs.get("sep", " ")

        # If printing to a specific file (not stdout), use original print
        if file is not None:
            original_print(*args, **kwargs)
            return

        # Convert args to string with the specified separator
        message = sep.join(str(arg) for arg in args)

        log_level = level
        if "debug" in message.lower():
            log_level = "DEBUG"
        elif "warning" in message.lower():
            log_level = "WARNING"
        elif "error" in message.lower():
            log_level = "ERROR"
        elif "critical" in message.lower():
            log_level = "CRITICAL"

        # Log the message
        log_window.log(message, level=log_level)

    # Replace the built-in print with our custom function
    builtins.print = custom_print

    # Return a function to restore the original print
    def restore_print():
        builtins.print = original_print
        return original_print

    return restore_print


class LogWindow:
    """Live updating CLI window to display progress and logs."""

    def __init__(
        self,
        title: str = "AgileMind",
        refresh_per_second: float = 5,
        display_style: Literal["tree", "table"] = "tree",
        log_height: int = 5,
        window_height: Optional[int] = None,
        intercept_print: bool = True,
        print_log_level: str = "INFO",
        auto_refresh: bool = True,
        interactive: bool = True,
    ):
        """
        Initialize the LogWindow.

        Args:
            title (str): The title of the window
            refresh_per_second (float): How many times per second the display refreshes
            display_style (Literal["tree", "table"]): Display style for tasks - "tree" or "table"
            log_height (int): Number of log lines to show in the log zone
            window_height (Optional[int]): Total height of the window. If None, uses full terminal height
            intercept_print (bool): Whether to automatically intercept print function calls
            print_log_level (str): Log level to use for intercepted print messages
            auto_refresh (bool): Whether to automatically refresh the window at regular intervals
            interactive (bool): Whether to show interactive window with rich.Live. If False, operates as a backend log collector.
        """
        self.title = title
        self.console = Console()
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.task_hierarchy: Dict[str, Optional[str]] = {}  # task_id -> parent_id
        self._live: Optional[Live] = None
        self.refresh_per_second = refresh_per_second
        self.display_style = display_style
        self.hidden = False
        self.interactive = interactive
        # Log storage
        self.logs: List[Tuple[datetime, str, str]] = []
        self.log_height = log_height
        self.window_height = window_height
        self.full_screen = window_height is None

        # Auto-refresh settings
        self.auto_refresh = (
            auto_refresh and interactive
        )  # Only auto-refresh in interactive mode
        self.auto_refresh_interval = 1.0 / refresh_per_second
        self._auto_refresh_thread = None
        self._stop_refresh_thread = threading.Event()

        # Store the print restore function
        self._restore_print = None

        # Intercept print if requested and in interactive mode
        if intercept_print and interactive:
            self._restore_print = self.intercept_print(level=print_log_level)

        self._calculate_heights()

    def _calculate_heights(self):
        """Calculate the heights of the different zones."""
        if self.full_screen and self.interactive:
            _, height = self.console.size
            self.window_height = height
            self.task_zone_height = max(1, self.window_height - self.log_height - 4)

    def __enter__(self):
        """Context manager entry point."""
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit point."""
        self.close()

    def open(self):
        """Open and display the log window."""
        if self.interactive:
            self._live = Live(
                self._generate_display(),
                console=self.console,
                refresh_per_second=self.refresh_per_second,
                screen=True,
            )
            self._live.start()
            self.hidden = False

            # Start auto-refresh thread if enabled
            if self.auto_refresh:
                self._start_auto_refresh()

        return self

    def close(self):
        """Close the log window."""
        # Stop the auto-refresh thread if it's running
        self._stop_auto_refresh()

        if self._live and self.interactive:
            self._live.stop()
            self._live = None
            self.hidden = False

        # Restore original print function if it was intercepted
        if self._restore_print is not None:
            self._restore_print()
            self._restore_print = None

    def hide(self):
        """Temporarily hide the log window without closing it."""
        if not self.interactive:
            return

        # Stop auto-refresh while hidden
        self._stop_auto_refresh()

        if self._live and not self.hidden:
            # Save current state before stopping
            self._saved_display = self._generate_display()
            self._live.stop()
            self._live = None
            self.hidden = True
            # Clear the screen to remove the display
            self.console.clear()

    def show(self):
        """Show the log window if it was hidden."""
        if not self.interactive:
            return

        if self.hidden:
            # Restart with the saved display
            self._live = Live(
                (
                    self._saved_display
                    if hasattr(self, "_saved_display")
                    else self._generate_display()
                ),
                console=self.console,
                refresh_per_second=self.refresh_per_second,
                screen=True,
            )
            self._live.start()
            self.hidden = False

            # Restart auto-refresh if enabled
            if self.auto_refresh:
                self._start_auto_refresh()

    def toggle_visibility(self):
        """Toggle the visibility of the log window."""
        if not self.interactive:
            return

        if self.hidden:
            self.show()
        else:
            self.hide()

    def add_task(
        self, description: str, parent_id: Optional[str] = None, status: str = "pending"
    ) -> str:
        """
        Add a new task to the window.

        Args:
            description (str): Description of the task
            parent_id (Optional[str]): Optional ID of the parent task
            status (str): Initial status of the task

        Returns:
            task_id: Identifier for the added task
        """
        task_id = str(uuid.uuid4())
        self.tasks[task_id] = {
            "description": description,
            "status": status,
            "time_added": datetime.now(),
        }
        self.task_hierarchy[task_id] = parent_id

        if self._live and self.interactive:
            self._live.update(self._generate_display())

        return task_id

    def complete_task(self, task_id: str):
        """
        Mark a task as completed.

        Args:
            task_id (str): ID of the task to complete
        """
        if task_id in self.tasks:
            self.tasks[task_id]["status"] = "completed"
            self.tasks[task_id]["time_completed"] = datetime.now()

            if self._live and self.interactive:
                self._live.update(self._generate_display())

    def update_task(self, task_id: str, status: str, description: Optional[str] = None):
        """
        Update a task's status and optionally its description.

        Args:
            task_id (str): ID of the task to update
            status (str): New status, e.g., "pending", "running", "completed", "failed"
            description (Optional[str]): New description (if provided)
        """
        if task_id in self.tasks:
            self.tasks[task_id]["status"] = status
            if description:
                self.tasks[task_id]["description"] = description

            if self._live and self.interactive:
                self._live.update(self._generate_display())

    def set_display_style(self, style: Literal["tree", "table"]):
        """
        Set the display style for the tasks.

        Args:
            style (Literal["tree", "table"]): Either "tree" or "table"
        """
        if style not in ["tree", "table"]:
            raise ValueError("Display style must be either 'tree' or 'table'")

        self.display_style = style
        if self._live and self.interactive:
            self._live.update(self._generate_display())

    def log(self, message: str, level: str = "INFO"):
        """
        Add a log message to the log zone.

        Args:
            message (str): The log message to add
            level (str): Log level (INFO, WARNING, ERROR, DEBUG, etc.)
        """
        timestamp = datetime.now()

        # Split multi-line messages and add each line as a separate log
        for line in message.split("\n"):
            if line.strip():
                self.logs.append((timestamp, level, line))

        # Maintain fixed size by removing oldest logs if in interactive mode
        # In non-interactive mode, keep all logs
        if self.interactive and len(self.logs) > self.log_height:
            self.logs = self.logs[-self.log_height :]

        # Update the display if live and interactive
        if self._live and self.interactive:
            self._live.update(self._generate_display())

        if not self.interactive:
            # print the log message to console if not in interactive mode
            print(Text(f"{level} - {message}"))

    def clear_logs(self):
        """Clear all logs from the log zone."""
        self.logs = []
        if self._live and self.interactive:
            self._live.update(self._generate_display())

    def intercept_print(self, level: str = "INFO") -> Callable:
        """
        Intercept the built-in print function and redirect output to this LogWindow.

        Args:
            level: Log level to use for the intercepted print messages

        Returns:
            A function to restore the original print function
        """
        return intercept_print(self, level)

    def _start_auto_refresh(self):
        """Start a background thread for auto-refreshing the display."""
        if (
            not self.interactive
            or self._auto_refresh_thread is not None
            and self._auto_refresh_thread.is_alive()
        ):
            return  # Thread already running or not in interactive mode

        self._stop_refresh_thread.clear()
        self._auto_refresh_thread = threading.Thread(
            target=self._auto_refresh_loop, daemon=True
        )
        self._auto_refresh_thread.start()

    def _stop_auto_refresh(self):
        """Stop the auto-refresh background thread."""
        if (
            self._auto_refresh_thread is not None
            and self._auto_refresh_thread.is_alive()
        ):
            self._stop_refresh_thread.set()
            self._auto_refresh_thread.join(timeout=1.0)
            self._auto_refresh_thread = None

    def _auto_refresh_loop(self):
        """Background thread loop to periodically update the display."""
        while not self._stop_refresh_thread.is_set():
            if self._live and not self.hidden and self.interactive:
                try:
                    self._live.update(self._generate_display())
                except Exception:
                    # Prevent crashes from display updates
                    pass
            time.sleep(self.auto_refresh_interval)

    def set_auto_refresh(self, enabled: bool, interval: Optional[float] = None):
        """
        Enable or disable automatic display refreshing.

        Args:
            enabled (bool): Whether to enable auto-refresh
            interval (Optional[float]): Refresh interval in seconds. If None, uses existing interval.
        """
        if not self.interactive:
            return

        self.auto_refresh = enabled
        if interval is not None:
            self.auto_refresh_interval = interval

        if enabled:
            self._start_auto_refresh()
        else:
            self._stop_auto_refresh()

    def _generate_display(self) -> Panel:
        """Generate the display content."""
        # Only calculate heights in interactive mode
        if self.interactive:
            self._calculate_heights()

        if self.display_style == "tree":
            max_items = max(1, self.task_zone_height - 1)
            tasks_display = self._generate_task_tree(max_items=max_items)
            tasks_size = tasks_display.count + 1
        else:
            max_rows = max(1, self.task_zone_height - 4)
            tasks_display = self._generate_task_table(max_rows=max_rows)
            tasks_size = tasks_display.row_count + 4

        # Calculate task zone padding needed
        task_zone_padding = max(0, self.task_zone_height - tasks_size)
        if task_zone_padding > 0:
            # Add padding to the task zone to maintain its allocated height
            tasks_display = Group(tasks_display, Text("\n" * task_zone_padding))

        # Create the log zone with guaranteed minimum height
        log_display = self._generate_log_zone()

        # Combine displays using Group which can handle any renderable
        combined_display = Group(tasks_display, Rule(style="dim"), log_display)

        return Panel(
            combined_display,
            title=f"[bold blue]{self.title}[/bold blue]",
            border_style="blue",
            box=box.ROUNDED,
            height=self.window_height,
        )

    def _generate_log_zone(self) -> Text:
        """Generate the log zone display."""
        log_text = Text()

        # If no logs, add placeholder
        if not self.logs:
            log_text.append("No logs", style="dim italic")
            return log_text

        # Add each log line with timestamp and level
        for i, (timestamp, level, message) in enumerate(self.logs):
            if i > 0:
                log_text.append("\n")

            # Format timestamp
            time_str = timestamp.strftime("%H:%M:%S")
            log_text.append(time_str, style="bright_black")

            # Add level with appropriate color
            log_text.append(" - ")
            log_text.append(level, style=self._get_level_style(level))

            # Add message
            log_text.append(" - ")
            log_text.append(message)

        # Pad with empty lines to maintain fixed height
        missing_lines = self.log_height - len(self.logs)
        for _ in range(missing_lines):
            log_text.append("\n")
            log_text.append("", style="dim")

        return log_text

    def _generate_task_tree(self, max_items: Optional[int] = None) -> Tree:
        """Generate a hierarchical tree of tasks.

        Args:
            max_items: Maximum number of items to show in the tree
        """
        tree = Tree("[bold]Task Hierarchy[/bold]")
        count = 0

        # Check if we even need to consider limits
        limited = max_items is not None and len(self.tasks) > max_items

        roots_found = False
        # Process root tasks first
        root_tasks = [
            (task_id, self.tasks[task_id])
            for task_id, parent in self.task_hierarchy.items()
            if parent is None
        ]

        # If we have root tasks, add them
        for task_id, task in root_tasks:
            # Check if we've reached the limit
            if limited and count >= max_items - 1:  # Save space for ellipsis
                tree.add("[dim]...[/dim]")
                count += 1
                break

            roots_found = True
            status_style = self._get_status_style(task["status"])

            # Format task info
            task_text = f"{task['description']} {status_style}"
            time_info = f"[dim](Added: {task['time_added'].strftime('%H:%M:%S')}"
            if "time_completed" in task:
                time_info += (
                    f", Completed: {task['time_completed'].strftime('%H:%M:%S')}"
                )
            time_info += ")[/dim]"

            branch = tree.add(f"{task_text} {time_info}")
            count += 1

            # Add children with remaining space
            remaining = None if not limited else max(0, max_items - count)
            child_count = self._add_child_tasks(branch, task_id, remaining)
            count += child_count

            # If we've reached the limit after adding children, stop
            if limited and count >= max_items:
                break

        # If no root tasks were found, create a flat tree
        if not roots_found and self.tasks:
            flat_task_items = list(self.tasks.items())

            # Calculate how many tasks we can show
            tasks_to_show = (
                len(flat_task_items)
                if not limited
                else min(max_items, len(flat_task_items))
            )

            for task_id, task in flat_task_items[:tasks_to_show]:
                status_style = self._get_status_style(task["status"])
                task_text = f"{task['description']} {status_style}"
                time_info = f"[dim](Added: {task['time_added'].strftime('%H:%M:%S')}"
                if "time_completed" in task:
                    time_info += (
                        f", Completed: {task['time_completed'].strftime('%H:%M:%S')}"
                    )
                time_info += ")[/dim]"

                tree.add(f"{task_text} {time_info}")
                count += 1

            # Add ellipsis if we limited
            if limited and len(flat_task_items) > tasks_to_show:
                tree.add("[dim]...[/dim]")
                count += 1

        tree.count = count
        return tree

    def _add_child_tasks(
        self, parent_branch, parent_id, remaining: Optional[int] = None
    ) -> int:
        """Add child tasks to a parent branch.

        Args:
            parent_branch: The branch to add children to
            parent_id: ID of the parent task
            remaining: Number of remaining slots available

        Returns:
            int: Number of nodes added
        """
        count = 0

        # Get all child tasks for this parent
        child_tasks = [
            (task_id, self.tasks[task_id])
            for task_id, parent in self.task_hierarchy.items()
            if parent == parent_id
        ]

        # Check for limiting
        limited = remaining is not None and len(child_tasks) > remaining

        # Determine how many children we can show
        tasks_to_show = len(child_tasks) if not limited else remaining

        for i, (task_id, task) in enumerate(child_tasks[:tasks_to_show]):
            status_style = self._get_status_style(task["status"])

            # Format task info
            task_text = f"{task['description']} {status_style}"
            time_info = f"[dim](Added: {task['time_added'].strftime('%H:%M:%S')}"
            if "time_completed" in task:
                time_info += (
                    f", Completed: {task['time_completed'].strftime('%H:%M:%S')}"
                )
            time_info += ")[/dim]"

            branch = parent_branch.add(f"{task_text} {time_info}")
            count += 1

            # Calculate remaining slots for next level
            next_remaining = None if remaining is None else max(0, remaining - count)

            # Add grandchildren if we have space left
            if next_remaining is None or next_remaining > 0:
                grandchild_count = self._add_child_tasks(
                    branch, task_id, next_remaining
                )
                count += grandchild_count

                # If we've used up all slots, stop adding more children
                if remaining is not None and count >= remaining:
                    break

        # Add ellipsis if we couldn't show all children
        if limited and len(child_tasks) > tasks_to_show:
            parent_branch.add("[dim]...[/dim]")
            count += 1

        return count

    def _generate_task_table(self, max_rows: Optional[int] = None) -> Table:
        """Generate a table of tasks.

        Args:
            max_rows: Maximum number of task rows to display (not including header)
        """
        table = Table(box=box.SIMPLE, show_header=True, header_style="bold")
        table.add_column("ID", style="dim", width=8)
        table.add_column("Description")
        table.add_column("Status", justify="center")
        table.add_column("Added", style="dim")
        table.add_column("Completed", style="dim")

        # Determine if we need to limit rows
        total_tasks = len(self.tasks)
        limited = max_rows is not None and total_tasks > max_rows
        rows_to_show = max_rows if limited else total_tasks

        # Add task rows
        for i, (task_id, task) in enumerate(list(self.tasks.items())[:rows_to_show]):
            status_style = self._get_status_style(task["status"])
            added_time = task["time_added"].strftime("%H:%M:%S")
            completed_time = (
                task.get("time_completed", "").strftime("%H:%M:%S")
                if "time_completed" in task
                else "-"
            )

            table.add_row(
                f"{i+1:2d}",
                task["description"],
                status_style,
                added_time,
                completed_time,
            )

        # Add ellipsis row if we limited the rows
        if limited:
            table.add_row("...", "...", "...", "...", "...")

        return table

    def _get_level_style(self, level: str) -> str:
        """Get the appropriate style for a log level."""
        level = level.upper()
        if level == "INFO":
            return "bright_blue"
        elif level == "WARNING":
            return "yellow"
        elif level == "ERROR":
            return "red"
        elif level == "DEBUG":
            return "green"
        elif level == "CRITICAL":
            return "red bold"
        elif level == "SUCCESS":
            return "green bold"
        else:
            return "cyan"

    def _get_status_style(self, status: str) -> str:
        """Get styled status text based on status value."""
        if status == "completed":
            return " [green]COMPLETED[/green]"
        elif status == "pending":
            return " [yellow]PENDING[/yellow]"
        elif status == "failed":
            return " [red]FAILED[/red]"
        elif status == "running":
            current_spinner_char = SPINNER[int(time.time() * 4) % 4]
            return f"[blue]{current_spinner_char} RUNNING[/blue]"
        else:
            return f" [cyan]{status.upper()}[/cyan]"
