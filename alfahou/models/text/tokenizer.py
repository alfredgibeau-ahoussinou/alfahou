from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


class CharTokenizer:
    """Tokenizer caractère — vocabulaire dérivé du corpus, zéro dépendance externe."""

    PAD = "<pad>"
    UNK = "<unk>"
    BOS = "<bos>"
    EOS = "<eos>"

    def __init__(self, stoi: dict[str, int] | None = None):
        if stoi is None:
            specials = [self.PAD, self.UNK, self.BOS, self.EOS]
            self.stoi = {s: i for i, s in enumerate(specials)}
            self.itos = {i: s for s, i in self.stoi.items()}
        else:
            self.stoi = dict(stoi)
            self.itos = {i: s for s, i in self.stoi.items()}

    @property
    def vocab_size(self) -> int:
        return len(self.stoi)

    def encode(self, text: str, add_special: bool = True) -> list[int]:
        ids: list[int] = []
        if add_special:
            ids.append(self.stoi[self.BOS])
        unk = self.stoi[self.UNK]
        for ch in text:
            ids.append(self.stoi.get(ch, unk))
        if add_special:
            ids.append(self.stoi[self.EOS])
        return ids

    def decode(self, ids: list[int], skip_special: bool = True) -> str:
        specials = {self.PAD, self.UNK, self.BOS, self.EOS}
        out: list[str] = []
        for i in ids:
            ch = self.itos.get(i, self.UNK)
            if skip_special and ch in specials:
                continue
            out.append(ch)
        return "".join(out)

    def build_from_text(self, text: str, min_freq: int = 1) -> "CharTokenizer":
        counts = Counter(text)
        specials = [self.PAD, self.UNK, self.BOS, self.EOS]
        chars = sorted(ch for ch, n in counts.items() if n >= min_freq and ch not in specials)
        stoi = {s: i for i, s in enumerate(specials)}
        for ch in chars:
            stoi[ch] = len(stoi)
        self.stoi = stoi
        self.itos = {i: s for s, i in stoi.items()}
        return self

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(self.stoi, ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "CharTokenizer":
        stoi = json.loads(path.read_text(encoding="utf-8"))
        return cls(stoi=stoi)
