from __future__ import annotations


def matched_friction_block_indices(total_steps: int, block_count: int) -> set[int]:
    if block_count <= 0:
        return set()
    if block_count >= total_steps:
        return set(range(total_steps))
    interval = total_steps / block_count
    return {min(total_steps - 1, int(i * interval)) for i in range(block_count)}
