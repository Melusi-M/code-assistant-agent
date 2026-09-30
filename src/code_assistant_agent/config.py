from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RepositoryConfig:
    root: Path

    def __post_init__(self) -> None:
        resolved_root = self.root.resolve()

        if not resolved_root.exists():
            raise ValueError(
                f"Repository does not exist: {resolved_root}"
            )

        if not resolved_root.is_dir():
            raise ValueError(
                f"Repository path is not a directory: {resolved_root}"
            )

        object.__setattr__(self, "root", resolved_root)