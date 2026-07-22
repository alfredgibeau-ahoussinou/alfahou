"""Conversation naturelle FR/EN — réponses directes, style chat (sans API cloud)."""

from __future__ import annotations

import random
import re
import unicodedata


def _norm(text: str) -> str:
    t = text.lower().strip()
    t = unicodedata.normalize("NFKC", t)
    t = re.sub(r"[!?.…]+$", "", t).strip()
    t = re.sub(r"\s+", " ", t)
    return t


def _pick(*options: str) -> str:
    return random.choice(options)


# Salutations → miroir + accroche naturelle
_GREET_FR = {
    "coucou": ("Coucou", "comment ça va ?"),
    "salut": ("Salut", "comment tu vas ?"),
    "bonjour": ("Bonjour", "comment ça va ?"),
    "bonsoir": ("Bonsoir", "tu vas bien ?"),
    "hey": ("Hey", "quoi de beau ?"),
    "hello": ("Hello", "comment ça va ?"),
    "hi": ("Hi", "ça va ?"),
    "yo": ("Yo", "ça roule ?"),
    "wesh": ("Wesh", "ça va ?"),
    "allô": ("Allô", "je t’écoute !"),
    "allo": ("Allô", "je t’écoute !"),
    "hola": ("Hola", "comment ça va ?"),
    "bien le bonjour": ("Bien le bonjour", "que puis-je faire pour toi ?"),
    "salutations": ("Salutations", "ravie de te lire."),
}

_GREET_EN = {
    "hi": ("Hi", "how’s it going?"),
    "hello": ("Hello", "how are you?"),
    "hey": ("Hey", "what’s up?"),
    "yo": ("Yo", "how’s it going?"),
    "good morning": ("Good morning", "how are you today?"),
    "good evening": ("Good evening", "how’s your day going?"),
    "good afternoon": ("Good afternoon", "how can I help?"),
}


def try_chitchat(prompt: str, lang: str, name: str | None = None) -> str | None:
    """Petit talk & formules sociales — réponses courtes et naturelles."""
    raw = prompt.strip()
    t = _norm(raw)
    who = f" {name}" if name else ""

    # Salutation seule (éventuellement avec ponctuation / emoji légers)
    bare = re.sub(r"[^\wàâäéèêëïîôùûüç\s'-]", "", t, flags=re.I).strip()
    greet_map = _GREET_FR if lang != "en" else _GREET_EN
    if bare in greet_map:
        hi, tail = greet_map[bare]
        if lang == "en":
            return f"{hi}{who}! {tail[0].upper() + tail[1:]}"
        return f"{hi}{who} ! {tail[0].upper() + tail[1:]}"

    # Salutation en tête d’une phrase courte
    for key, (hi, tail) in greet_map.items():
        if bare.startswith(key + " ") and len(bare.split()) <= 4:
            rest = bare[len(key) :].strip()
            if lang == "en":
                return f"{hi}{who}! {tail[0].upper() + tail[1:]}" if not rest else f"{hi}{who}! {rest[0].upper() + rest[1:]} — I’m here."
            return f"{hi}{who} ! {tail[0].upper() + tail[1:]}"

    # Ça va / how are you (question)
    if re.fullmatch(
        r"(ça|ca) va\??|comment (ça|ca) va|tu vas bien|vous allez bien|"
        r"how are you( doing)?|how'?s it going|what'?s up|wassup",
        bare,
    ) or re.fullmatch(r"(ça|ca) va bien\?", bare):
        if lang == "en":
            return _pick(
                f"I’m good{who}, thanks! How about you?",
                f"Doing well{who}! What’s on your mind?",
            )
        return _pick(
            f"Ça va bien{who}, merci ! Et toi ?",
            f"Tranquille{who} ! Et de ton côté ?",
            f"Nickel{who}. Et toi, tu vas bien ?",
        )

    # Affirmation « ça va bien » / « je vais bien » (pas la question « ça va »)
    if re.fullmatch(
        r"(bien|super|nickel|cool|top)|(ça|ca) va bien( et toi)?|je vais bien|"
        r"good|great|fine|i'?m (good|fine|ok|okay)",
        bare,
    ):
        if lang == "en":
            return "Glad to hear it. What do you want to do?"
        return _pick("Content de l’entendre. Qu’est-ce qu’on fait ?", "Parfait. Dis-moi ce dont tu as besoin.")

    if re.fullmatch(r"(quoi de (neuf|beau)|tu fais quoi|what'?s new|what are you (up to|doing))", bare):
        if lang == "en":
            return "Ready to help — writing, ideas, images, video, PDF… What do you need?"
        return "Je suis là, prêt à t’aider — texte, idées, image, vidéo, PDF… Tu veux quoi ?"

    if re.search(r"\b(merci|thanks|thank you|thx|merci beaucoup|thanks a lot)\b", t) and len(t.split()) <= 6:
        if lang == "en":
            return _pick("You’re welcome!", "Anytime.", "Happy to help.")
        return _pick("Avec plaisir !", "De rien.", "Quand tu veux.")

    if re.fullmatch(
        r"(ok|okay|d'?accord|dac|entendu|parfait|super|cool|nice|yes|oui|ouais|yep|yeah|nan|non|nope|no)",
        bare,
    ):
        if lang == "en":
            return _pick("Got it. What’s next?", "Alright — tell me more.", "OK. I’m listening.")
        return _pick("OK. Je t’écoute.", "Noté. La suite ?", "D’accord — dis-moi.")

    if re.fullmatch(
        r"(bye|ciao|à\s*\+|a\s*\+|à plus|a plus|à bientôt|au revoir|bonne (nuit|journée|soirée)|see you|goodbye|good night)",
        bare,
    ):
        if lang == "en":
            return _pick("See you soon!", "Take care!", "Bye — come back anytime.")
        return _pick("À plus !", "À bientôt.", "Bonne continuation !")

    if re.fullmatch(r"(lol|mdr|ptdr|haha+|héhé|hehe|😂|😅)", bare):
        if lang == "en":
            return "Haha 😄 What’s next?"
        return "Haha 😄 Dis-moi la suite."

    if re.search(r"\b(je (m'?ennuie|suis (perdu|perdue|bloqué|bloquee|bloquée|fatigué|fatiguee|fatiguée)))\b", t):
        if lang == "en":
            return "I’m here. Want a fun idea, a short story, or something useful to unblock you?"
        return "Je suis là. Tu veux une idée fun, une mini-histoire, ou un coup de main concret pour débloquer ?"

    if re.fullmatch(r"(test|testing|ping|coucou test)", bare):
        if lang == "en":
            return "Pong — I’m online. Say anything."
        return "Reçu — je suis en ligne. Envoie ce que tu veux."

    return None


def _is_question(t: str) -> bool:
    if "?" in t:
        return True
    return bool(
        re.match(
            r"^(qui|que|quoi|quand|où|ou|pourquoi|comment|combien|est[- ]ce que|peux[- ]tu|peut[- ]on|"
            r"c'?est quoi|qu'?est[- ]ce|what|who|when|where|why|how|which|can you|do you|is it|are you)\b",
            t,
            re.I,
        )
    )


def _strip_task_verbs(prompt: str) -> str:
    t = prompt.strip()
    t = re.sub(
        r"^(s'il te plaît|s'il vous plaît|svp|please|peux[- ]tu|pourrais[- ]tu|can you|could you)\s+",
        "",
        t,
        flags=re.I,
    )
    t = re.sub(
        r"^(dis[- ]moi|explique[- ]moi|rappelle[- ]moi|tell me|explain|say)\s+",
        "",
        t,
        flags=re.I,
    )
    return t.strip(" \n\t.:;")


def direct_answer(prompt: str, lang: str, mode: str, name: str | None = None) -> str:
    """Réponse générale naturelle quand aucun skill spécialisé ne matche."""
    hello = f"{name}, " if name else ""
    t = prompt.strip()
    low = t.lower()

    # Questions personnelles courtes
    if re.search(r"\b(tu (vas|vas bien|fais quoi|es qui|es là)|you (there|ok|good))\b", low) and len(t) < 60:
        chat = try_chitchat(t, lang, name)
        if chat:
            return chat

    if _is_question(low):
        topic = _strip_task_verbs(t)
        if re.search(r"\b(c'?est quoi|qu'?est[- ]ce que|what is|what'?s|who is)\b", low):
            subject = re.sub(
                r"^(c'?est quoi|qu'?est[- ]ce que c'?est|qu'?est[- ]ce que|what is|what'?s|who is)\s+",
                "",
                topic,
                flags=re.I,
            ).strip(" ?")
            subject = subject or topic
            if lang == "en":
                return (
                    f"{hello}**{subject[:1].upper() + subject[1:]}** — here’s a straight take:\n\n"
                    f"In short: it’s a topic worth unpacking clearly. "
                    f"The useful angle is what it does in practice, why people care, and one concrete example.\n\n"
                    f"Want it simpler, deeper, or as a short paragraph you can copy?"
                )
            return (
                f"{hello}**{subject[:1].upper() + subject[1:]}** — version directe :\n\n"
                f"En gros : c’est un sujet qu’on peut expliquer simplement. "
                f"L’essentiel, c’est à quoi ça sert concrètement, pourquoi ça compte, et un exemple clair.\n\n"
                f"Tu veux plus simple, plus détaillé, ou un paragraphe prêt à coller ?"
            )

        if re.search(r"\b(comment|how (to|do|can))\b", low):
            if lang == "en":
                return (
                    f"{hello}Here’s a direct way:\n\n"
                    f"1. Clarify the goal in one sentence.\n"
                    f"2. Do the smallest useful step first.\n"
                    f"3. Check the result, then iterate.\n\n"
                    f"About « {topic} »: start simple, avoid overbuilding, and ask me for the next step when you’re ready."
                )
            return (
                f"{hello}Voici une façon directe :\n\n"
                f"1. Clarifie l’objectif en une phrase.\n"
                f"2. Fais le plus petit pas utile tout de suite.\n"
                f"3. Vérifie le résultat, puis itère.\n\n"
                f"Pour « {topic} » : reste simple, évite de tout surcharger, et demande-moi l’étape suivante quand tu veux."
            )

        if re.search(r"\b(pourquoi|why)\b", low):
            if lang == "en":
                return (
                    f"{hello}Usually for a few reasons: a clear need, a practical benefit, and a better outcome than doing nothing.\n\n"
                    f"On « {topic} », the short answer is: it helps you move forward with less friction. "
                    f"Want a deeper why?"
                )
            return (
                f"{hello}En général pour trois raisons : un besoin clair, un bénéfice concret, et un meilleur résultat que de ne rien faire.\n\n"
                f"Sur « {topic} », la réponse courte : ça aide à avancer avec moins de friction. "
                f"Tu veux le pourquoi plus détaillé ?"
            )

        # Question ouverte
        if lang == "en":
            return (
                f"{hello}Straight answer: yes — we can work on that.\n\n"
                f"You asked about **{topic}**. Tell me if you want a short explanation, a list, a draft text, "
                f"or something visual (image / video / PDF)."
            )
        return (
            f"{hello}Réponse directe : oui — on peut traiter ça.\n\n"
            f"Tu parles de **{topic}**. Dis-moi si tu veux une explication courte, une liste, un texte rédigé, "
            f"ou quelque chose de visuel (image / vidéo / PDF)."
        )

    # Demande d’écriture / message libre → produire un texte naturel
    if re.search(
        r"\b(écris|ecris|rédige|redige|write|compose|invente|raconte|dis quelque chose|"
        r"fais[- ]moi|donne[- ]moi|je veux|j'aimerais|j’aimerais)\b",
        low,
    ):
        topic = _strip_task_verbs(t)
        topic = re.sub(
            r"^(écris|ecris|rédige|redige|write|compose|invente|raconte|fais[- ]moi|donne[- ]moi|"
            r"un |une |le |la |les |des |a |an |the )+",
            "",
            topic,
            flags=re.I,
        ).strip()
        if lang == "en":
            title = topic[:1].upper() + topic[1:] if topic else "Here you go"
            return (
                f"{hello}{title}\n\n"
                f"Here’s a clear draft you can use as-is or tweak.\n\n"
                f"{title} matters when you keep the message human: one idea, plain words, and a concrete next step. "
                f"Start with the point, add one detail that feels real, then close with an invitation to continue.\n\n"
                f"Want it shorter, warmer, or more formal?"
            )
        title = topic[:1].upper() + topic[1:] if topic else "Voilà"
        return (
            f"{hello}{title}\n\n"
            f"Voici un texte direct, prêt à reprendre.\n\n"
            f"{title} — l’essentiel, c’est de rester humain : une idée claire, des mots simples, et une suite concrète. "
            f"On pose le propos, on ajoute un détail vrai, puis on ouvre la conversation.\n\n"
            f"Tu le veux plus court, plus chaleureux, ou plus formel ?"
        )

    # Message libre / opinion / phrase quelconque → répondre comme un interlocuteur
    words = t.split()
    if len(words) <= 12 and not re.search(r"\b(image|vidéo|video|pdf|code|plan|traduis)\b", low):
        # Refléter et engager, sans catalogue de features
        mirrored = t[:1].upper() + t[1:] if t else t
        if lang == "en":
            return _pick(
                f"{hello}{mirrored} — I’m with you. What do you want to do with that?",
                f"{hello}Got it: {mirrored.rstrip('.')}. Tell me how I can help — explain, rewrite, or create something.",
                f"{hello}OK. About that: what’s your goal? A reply, an idea, or a finished text?",
            )
        return _pick(
            f"{hello}{mirrored} — je te suis. Tu veux en faire quoi ?",
            f"{hello}OK, j’ai capté : {mirrored.rstrip('.')}. Tu veux que je t’explique, que je reformule, ou que je crée quelque chose ?",
            f"{hello}Compris. Et concrètement, tu vises quoi — une réponse, une idée, ou un texte prêt ?",
        )

    # Texte plus long → synthèse + suite utile
    snippet = t if len(t) < 280 else t[:277] + "…"
    if mode == "teacher":
        if lang == "en":
            return (
                f"{hello}Let’s take this cleanly.\n\n"
                f"You said: « {snippet} »\n\n"
                f"**In one sentence:** the point is to make that idea usable.\n"
                f"**Next:** ask me to explain, simplify, or expand one part."
            )
        return (
            f"{hello}On prend ça proprement.\n\n"
            f"Tu as dit : « {snippet} »\n\n"
            f"**En une phrase :** l’idée, c’est de rendre ça utilisable.\n"
            f"**Suite :** demande-moi d’expliquer, simplifier, ou développer une partie."
        )
    if mode == "creative":
        if lang == "en":
            return (
                f"{hello}Creative take on what you wrote:\n\n"
                f"« {snippet} » — I’d turn that into a bold line, a short scene, or a visual prompt.\n\n"
                f"Which one do you want me to flesh out?"
            )
        return (
            f"{hello}Angle créatif sur ce que tu as écrit :\n\n"
            f"« {snippet} » — j’en ferais une accroche forte, une petite scène, ou un prompt visuel.\n\n"
            f"Je développe lequel ?"
        )
    if mode == "precise":
        if lang == "en":
            return (
                f"{hello}**Received**\n{snippet}\n\n"
                f"**Action**\nTell me the exact output: answer, list, email, code, image, video, or PDF."
            )
        return (
            f"{hello}**Reçu**\n{snippet}\n\n"
            f"**Action**\nDis-moi le livrable exact : réponse, liste, mail, code, image, vidéo ou PDF."
        )

    if lang == "en":
        return (
            f"{hello}I hear you.\n\n"
            f"« {snippet} »\n\n"
            f"Here’s the direct path: say what you want out of this — a clear answer, a rewritten text, "
            f"a plan, or a media file — and I’ll do that next, without fluff."
        )
    return (
        f"{hello}Je t’ai lu.\n\n"
        f"« {snippet} »\n\n"
        f"Version directe : dis-moi ce que tu veux en sortir — une réponse claire, un texte réécrit, "
        f"un plan, ou un média — et je le fais, sans blabla."
    )
