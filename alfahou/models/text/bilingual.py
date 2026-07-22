from __future__ import annotations

import re
import unicodedata


def detect_lang(text: str) -> str:
    """Détection FR/EN légère (sans dépendance externe)."""
    t = text.lower()
    fr_hits = len(
        re.findall(
            r"\b(bonjour|salut|merci|français|quoi|comment|peux|veux|écrire|écris|rédige|image|vidéo|document|aide|qui|je|suis|pour|avec|dans|une|des|les|mon|ma|mes|sur|paragraphe|texte)\b",
            t,
        )
    )
    en_hits = len(
        re.findall(
            r"\b(hello|hi|hey|thanks|please|what|how|can|write|image|video|document|help|who|are|you|the|and|for|with|my|create|make|about|paragraph|text|short)\b",
            t,
        )
    )
    if any(c in "éèêëàâùûüôîïç" for c in t):
        fr_hits += 2
    if en_hits > fr_hits:
        return "en"
    return "fr"


def classify_intent(text: str) -> str:
    t = text.lower().strip()
    if re.fullmatch(
        r"(bonjour|salut|bonsoir|coucou|yo|wesh|all[oô]|hey|hi|hello|"
        r"good\s*(morning|evening|afternoon))[!?.]*",
        t,
    ):
        return "greeting"
    if re.search(r"\b(merci|thanks|thank you)\b", t):
        return "thanks"
    if re.search(r"\b(aide|help|comment (ça|ca) marche|how (do|does|to)|what can you)\b", t):
        return "help"
    # Présentation seulement — pas « write about X »
    if re.search(
        r"\b(qui es[- ]tu|who are you|c'?est quoi alfahou|what (is|are) (you|alfahou)|présente[- ]toi|tell me about yourself|about you|about alfahou)\b",
        t,
    ) or re.fullmatch(r"(about|à propos)[!?.]*", t):
        return "about"
    if re.search(r"\b(capacités|capabilities|que sais[- ]tu|what can you do|fonctionnalités|features)\b", t):
        return "capabilities"
    if re.search(r"\b(anglais|english|speak english|in english)\b", t) and not re.search(
        r"\b(write|rédige|text|texte|image|video|vidéo|pdf)\b", t
    ):
        return "switch_en"
    if re.search(r"\b(français|francais|speak french|en français|in french)\b", t) and not re.search(
        r"\b(write|rédige|text|texte|image|video|vidéo|pdf)\b", t
    ):
        return "switch_fr"
    return "compose"


RESPONSES: dict[str, dict[str, str]] = {
    "greeting": {
        "fr": "Coucou ! Comment ça va ?",
        "en": "Hey! How’s it going?",
    },
    "thanks": {
        "fr": "Avec plaisir. Si tu veux autre chose — texte, image, vidéo ou PDF — je suis là.",
        "en": "You’re welcome. If you need anything else — text, image, video, or PDF — just ask.",
    },
    "help": {
        "fr": (
            "Voici comment utiliser AlfAhou :\n\n"
            "1. Choisis une modalité (Texte, Image, Vidéo, PDF) ou laisse Auto.\n"
            "2. Écris clairement ta demande en français ou en anglais.\n"
            "3. Exemples :\n"
            "   • « Rédige un paragraphe sur l’innovation »\n"
            "   • « Write a short intro about AlfAhou »\n"
            "   • « Image : cercle rouge vif »\n"
            "   • « PDF : résumé du projet »"
        ),
        "en": (
            "Here’s how to use AlfAhou:\n\n"
            "1. Pick a modality (Text, Image, Video, PDF) or leave Auto.\n"
            "2. Write a clear request in French or English.\n"
            "3. Examples:\n"
            "   • “Write a paragraph about innovation”\n"
            "   • “Rédige une intro sur AlfAhou”\n"
            "   • “Image: bright red circle”\n"
            "   • “PDF: project summary”"
        ),
    },
    "about": {
        "fr": (
            "Je m’appelle AlfAhou — contraction d’Alfred et Ahoussinou.\n\n"
            "Je suis une IA maison : transformer pour le texte, diffusion pour l’image, "
            "animation pour la vidéo, composition pour les PDF. Pas d’API cloud tierce : "
            "les modèles tournent pour Alfred Ahoussinou."
        ),
        "en": (
            "My name is AlfAhou — a blend of Alfred and Ahoussinou.\n\n"
            "I’m a homemade AI: a transformer for text, diffusion for images, "
            "motion for video, and layout for PDFs. No third-party cloud API — "
            "the models run for Alfred Ahoussinou."
        ),
    },
    "capabilities": {
        "fr": (
            "Mes capacités :\n"
            "• Texte — réponses claires en français et en anglais\n"
            "• Image — formes et scènes via diffusion locale\n"
            "• Vidéo — animation à partir d’une image\n"
            "• PDF — document structuré prêt à télécharger"
        ),
        "en": (
            "My capabilities:\n"
            "• Text — clear answers in French and English\n"
            "• Image — shapes and scenes via local diffusion\n"
            "• Video — animation from a generated image\n"
            "• PDF — structured document ready to download"
        ),
    },
    "switch_en": {
        "fr": "OK — I’ll reply in English. How can I help?",
        "en": "OK — I’ll reply in English. How can I help?",
    },
    "switch_fr": {
        "fr": "D’accord — je réponds en français. Comment puis-je t’aider ?",
        "en": "D’accord — je réponds en français. Comment puis-je t’aider ?",
    },
}


def _topic_from_prompt(prompt: str) -> str:
    cleaned = prompt.strip()
    cleaned = re.sub(r"^(please|s'il te plaît|s'il vous plaît|svp)\s+", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(
        r"^(rédige|redige|ecris|écris|write|create|make|generate|compose)\s+",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"^(un |une |a |an |the |le |la |les |des )?(court |short |petit |small )?"
        r"(texte|text|paragraphe|paragraph|article|intro|introduction|summary|résumé|resume)\s+",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"^(sur|about|on|de|du|des|d'|concerning)\s+", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .,:;!-")
    cleaned = re.sub(r"\bl\s+", "l'", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bd\s+", "d'", cleaned, flags=re.IGNORECASE)
    return cleaned or prompt.strip()


def compose_text(prompt: str, lang: str) -> str:
    """Rédaction structurée bilingue — phrases cohérentes, pas de charabia."""
    topic = _topic_from_prompt(prompt)
    topic_disp = topic[:1].upper() + topic[1:] if topic else ("Sujet" if lang == "fr" else "Topic")

    if lang == "en":
        return (
            f"{topic_disp}\n\n"
            f"{topic_disp} is a clear and useful subject to explore. "
            f"AlfAhou, the multimedia AI created by Alfred Ahoussinou, can help you describe it, "
            f"illustrate it with an image, animate it as a short video, or export it as a PDF.\n\n"
            f"In practice, start with a precise goal, then choose the right modality: "
            f"text for explanation, image for a visual, video for motion, PDF for a shareable document. "
            f"Working in English or French, AlfAhou keeps the message simple, direct, and actionable.\n\n"
            f"Next step: tell AlfAhou what you want to create about “{topic}” — "
            f"a summary, a pitch, an illustration, or a short report."
        )

    return (
        f"{topic_disp}\n\n"
        f"{topic_disp} est un sujet clair et utile à développer. "
        f"AlfAhou, l’IA multimédia conçue par Alfred Ahoussinou, peut t’aider à l’expliquer, "
        f"l’illustrer par une image, l’animer en vidéo courte, ou l’exporterer en PDF.\n\n"
        f"En pratique, commence par un objectif précis, puis choisis la bonne modalité : "
        f"texte pour expliquer, image pour visualiser, vidéo pour le mouvement, PDF pour partager. "
        f"En français comme en anglais, AlfAhou vise un message simple, direct et actionnable.\n\n"
        f"Prochaine étape : dis à AlfAhou ce que tu veux créer sur « {topic} » — "
        f"un résumé, un pitch, une illustration, ou un court rapport."
    )


def bilingual_reply(prompt: str) -> str | None:
    """Réponse conversationnelle FR/EN si l’intention est claire ; sinon None."""
    from alfahou.agent.converse import direct_answer, try_chitchat

    lang = detect_lang(prompt)
    chat = try_chitchat(prompt, lang)
    if chat:
        return chat
    intent = classify_intent(prompt)
    if intent == "compose":
        if len(prompt.strip()) >= 3:
            return direct_answer(prompt, lang, "balanced", None)
        return None
    if intent in ("switch_en", "switch_fr"):
        lang = "en" if intent == "switch_en" else "fr"
    if intent == "greeting":
        # filet de sécurité si try_chitchat n’a pas matché
        return "Coucou ! Comment ça va ?" if lang == "fr" else "Hey! How’s it going?"
    return RESPONSES[intent][lang]
