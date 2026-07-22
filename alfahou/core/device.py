from __future__ import annotations

import torch


def get_device() -> torch.device:
    if torch.backends.mps.is_available():
        return torch.device("mps")
    if torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


DEVICE = get_device()

# Limite les threads CPU pour des réponses plus stables sur free tier
if DEVICE.type == "cpu":
    torch.set_num_threads(max(1, min(2, torch.get_num_threads())))
