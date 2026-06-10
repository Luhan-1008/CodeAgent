"""
Stage module for organizing tasks within a pipeline.
"""

from agilemind.task import Task
from agilemind.context import Context
from agilemind.execution import Executor
from dataclasses import dataclass, field


@dataclass
class Stage:
    """A stage in a pipeline, containing one or more tasks to be executed."""

    name: str
    description: str = None
    tasks: list[Task] = field(default_factory=list)

    def __post_init__(self):
        if not self.name:
            raise ValueError("Stage must have a name")

    def add_task(self, *tasks: Task) -> "Stage":
        """
        Add one or more tasks to the stage.

        Args:
            tasks: The task(s) to add

        Returns:
            Self for chaining
        """
        self.tasks.extend(tasks)
        return self

    def execute(self, context: Context) -> Context:
        """
        Execute all tasks in the stage and update the context.

        Args:
            context: Current pipeline context

        Returns:
            Updated context with task results
        """

        executor: Executor = context.get("executor")
        if not executor:
            raise ValueError("No executor found in context")

        for i, task in enumerate(self.tasks):
            try:
                context = executor.execute(task, context)

                # Stop execution if task failed and we're not set to continue
                if task.get_status() == "failed" and not context.get(
                    "continue_on_failure", False
                ):
                    break

            except Exception as e:
                context[f"task_{task.name}_error"] = str(e)
                if not context.get("continue_on_failure", False):
                    raise

        return context
