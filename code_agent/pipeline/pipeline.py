"""
Pipeline module for orchestrating the flow of data through a series of agents.
"""

from typing import List, Optional
from agilemind.stage import Stage
from agilemind.context import Context
from dataclasses import dataclass, field


@dataclass
class Pipeline:
    """
    Pipeline class that orchestrates the flow between stages of tasks.
    """

    name: str
    description: Optional[str] = None
    stages: List[Stage] = field(default_factory=list)
    context: Context = field(default_factory=Context)

    def __post_init__(self):
        """Check that the pipeline has a name."""
        if not self.name:
            raise ValueError("Pipeline name is required")

    def register_executor(self, executor):
        self.context.executor = executor

    def add_stage(self, *stages: Stage) -> "Pipeline":
        """
        Add one or more stages to the pipeline.

        Args:
            *stages: One or more pipeline stages to add

        Returns:
            Self for chaining
        """
        self.stages.extend(stages)
        return self

    def run(self) -> Context:
        """
        Run the entire pipeline from start to finish.

        Args:
            initial_context: Initial context data to start with

        Returns:
            Final context after all stages have executed
        """
        for i, stage in enumerate(self.stages):
            try:
                self.context = stage.execute(self.context)
                self.context.set_metadata("last_executed_stage", stage.name)
            except Exception as e:
                self.context.set_metadata("failed_stage", stage.name)
                self.context.set_metadata("error", str(e))
                raise

        return self.context

    def run_until(self, stage_name: str) -> Context:
        """
        Run the pipeline until a specific stage is reached.

        Args:
            stage_name: Name of the stage to stop at (inclusive)
            initial_context: Initial context data to start with

        Returns:
            Context after executing up to and including the specified stage
        """
        for stage in self.stages:
            context_dict = self.context.to_dict()
            updated_context = stage.execute(context_dict)
            self.context.update(updated_context)
            self.context.set_metadata("last_executed_stage", stage.get_name())
            if stage.get_name() == stage_name:
                break

        return self.context
