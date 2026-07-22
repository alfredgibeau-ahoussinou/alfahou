from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path


class WordTokenizer:
    """Tokenizer mots + ponctuation — bien meilleur que le caractère pour FR/EN."""

    PAD = "<pad>"
    UNK = "<unk>"
    BOS = "<bos>"
    EOS = "<eos>"
    USER = "<user>"
    ASSIST = "<alfahou>"

    _token_re = re.compile(r"\w+|[^\w\s]", re.UNICODE)

    def __init__(self, stoi: dict[str, int] | None = None):
        if stoi is None:
            specials = [self.PAD, self.UNK, self.BOS, self.EOS, self.USER, self.ASSIST]
            self.stoi = {s: i for i, s in enumerate(specials)}
            self.itos = {i: s for s, i in self.stoi.items()}
        else:
            self.stoi = dict(stoi)
            self.itos = {i: s for s, i in self.stoi.items()}

    @property
    def vocab_size(self) -> int:
        return len(self.stoi)

    def tokenize(self, text: str) -> list[str]:
        return self._token_re.findall(text.lower())

    def encode(self, text: str, add_special: bool = True) -> list[int]:
        ids: list[int] = []
        if add_special:
            ids.append(self.stoi[self.BOS])
        unk = self.stoi[self.UNK]
        for tok in self.tokenize(text):
            ids.append(self.stoi.get(tok, unk))
        if add_special:
            ids.append(self.stoi[self.EOS])
        return ids

    def decode(self, ids: list[int], skip_special: bool = True) -> str:
        specials = {self.PAD, self.UNK, self.BOS, self.EOS, self.USER, self.ASSIST}
        punct = set(".,!?;:…»«\"'’”)(")
        out: list[str] = []
        for i in ids:
            tok = self.itos.get(i, self.UNK)
            if skip_special and tok in specials:
                continue
            if not out:
                out.append(tok)
            elif tok in punct or (out[-1] and out[-1] in {"'", "’", "-", "/"}):
                out.append(tok)
            else:
                out.append(" " + tok)
        text = "".join(out)
        # Remet une majuscule en début de phrase
        if text:
            text = text[0].upper() + text[1:]
        return text

    def build_from_text(self, text: str, min_freq: int = 1) -> "WordTokenizer":
        counts = Counter(self.tokenize(text))
        specials = [self.PAD, self.UNK, self.BOS, self.EOS, self.USER, self.ASSIST]
        words = sorted(w for w, n in counts.items() if n >= min_freq and w not in specials)
        stoi = {s: i for i, s in enumerate(specials)}
        for w in words:
            stoi[w] = len(stoi)
        self.stoi = stoi
        self.itos = {i: s for s, i in stoi.items()}
        return self

    def save(self, path: Path) -> None:
        path.write_text(
            json.dumps({"type": "word", "stoi": self.stoi}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path: Path) -> "WordTokenizer":
        raw = json.loads(path.read_text(encoding="utf-8"))
        stoi = raw["stoi"] if isinstance(raw, dict) and "stoi" in raw else raw
        return cls(stoi=stoi)


# Alias de compat pour anciens imports
CharTokenizer = WordTokenizer
