"""In-memory defaults for the Phase 3 desktop; persistence belongs to Phase 4."""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True, slots=True)
class DesktopSettings:
    """Initial destination and bounded fake-worker concurrency."""

    output_dir: Path = field(default_factory=lambda: Path.home() / "Downloads")
    parallel_limit: int = 2

    def __post_init__(self) -> None:
        """Reject concurrency outside the supported desktop range."""
        if type(self.parallel_limit) is not int or not 1 <= self.parallel_limit <= 4:
            raise ValueError("Parallel limit must be an integer from 1 to 4.")
