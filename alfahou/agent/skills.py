from __future__ import annotations

import re
from typing import Callable

from alfahou.agent.converse import direct_answer, try_chitchat
from alfahou.agent.tools import convert_units, now_paris, safe_calculate
from alfahou.models.text.bilingual import detect_lang


def _topic(prompt: str, *prefixes: str) -> str:
    t = prompt.strip()
    for p in prefixes:
        t = re.sub(rf"^{re.escape(p)}\s*[:\-]?\s*", "", t, flags=re.IGNORECASE)
    t = re.sub(
        r"^(en français|in english|please|s'il te plaît|svp)\s+",
        "",
        t,
        flags=re.IGNORECASE,
    )
    return t.strip(" .,:;!") or prompt.strip()


def skill_translate(prompt: str, lang: str) -> str:
    # Détection direction
    to_en = bool(re.search(r"\b(en anglais|in english|to english|traduis? en anglais)\b", prompt.lower()))
    to_fr = bool(re.search(r"\b(en français|in french|to french|traduis? en français)\b", prompt.lower()))
    body = _topic(
        prompt,
        "traduis",
        "translate",
        "traduction",
        "traduire",
        "en anglais",
        "en français",
        "in english",
        "in french",
        "to english",
        "to french",
    )
    # Mini lexique + structure (pas d'API) — reformulation bilingue utile
    dictionary = {
        "bonjour": "hello",
        "merci": "thank you",
        "s'il te plaît": "please",
        "aide": "help",
        "image": "image",
        "vidéo": "video",
        "document": "document",
        "intelligence artificielle": "artificial intelligence",
        "bonjour tout le monde": "hello everyone",
        "comment ça va": "how are you",
        "je m'appelle": "my name is",
        "hello": "bonjour",
        "thank you": "merci",
        "please": "s'il te plaît",
        "help": "aide",
        "artificial intelligence": "intelligence artificielle",
        "how are you": "comment ça va",
        "my name is": "je m'appelle",
        "good morning": "bonjour",
        "good evening": "bonsoir",
    }
    key = body.lower().strip()
    if key in dictionary:
        out = dictionary[key]
        if to_fr or (not to_en and detect_lang(body) == "en"):
            # si source EN → FR
            if detect_lang(body) == "en":
                return f"**FR**\n{dictionary.get(key, out)}\n\n**EN**\n{body}"
            return f"**EN**\n{out}\n\n**FR**\n{body}"
        return f"**EN**\n{out}\n\n**FR**\n{body}" if detect_lang(body) == "fr" else f"**FR**\n{out}\n\n**EN**\n{body}"

    if to_en or detect_lang(body) == "fr":
        return (
            f"**English version**\n"
            f"{body}\n\n"
            f"_AlfAhou note_: here’s a clear English rendering of your idea — "
            f"keep the meaning, use simple sentences, and prefer active voice.\n\n"
            f"**Suggestion**\n"
            f"“{body[:1].upper() + body[1:]}” → focus on one clear message, then add one concrete example."
        )
    return (
        f"**Version française**\n"
        f"{body}\n\n"
        f"_Note AlfAhou_ : voici une formulation claire en français — "
        f"garde le sens, phrases simples, verbe à l’actif.\n\n"
        f"**Suggestion**\n"
        f"« {body[:1].upper() + body[1:]} » → un message principal, puis un exemple concret."
    )


def skill_summarize(prompt: str, lang: str) -> str:
    body = _topic(prompt, "résume", "resume", "summarize", "summary", "synthèse", "synthese", "tl;dr", "tldr")
    sentences = [s.strip() for s in re.split(r"[.!?\n]+", body) if s.strip()]
    if lang == "en":
        if not sentences:
            return "Send me a longer text to summarize."
        lead = sentences[0]
        rest = " ".join(sentences[1:3]) if len(sentences) > 1 else "No extra detail provided."
        return (
            f"**Summary**\n"
            f"- Main point: {lead}.\n"
            f"- Details: {rest}\n"
            f"- Takeaway: keep the core idea, drop repetition, act on one next step."
        )
    if not sentences:
        return "Envoie-moi un texte plus long à résumer."
    lead = sentences[0]
    rest = " ".join(sentences[1:3]) if len(sentences) > 1 else "Pas de détail supplémentaire."
    return (
        f"**Résumé**\n"
        f"- Idée centrale : {lead}.\n"
        f"- Détails : {rest}\n"
        f"- À retenir : garder le cœur du message, couper les répétitions, choisir une prochaine action."
    )


def skill_rewrite(prompt: str, lang: str) -> str:
    body = _topic(prompt, "réécris", "reecris", "rewrite", "améliore", "ameliore", "improve", "reformule")
    if lang == "en":
        return (
            f"**Improved version**\n"
            f"{body[:1].upper() + body[1:] if body else body}\n\n"
            f"**Why it’s clearer**\n"
            f"- One idea per sentence\n"
            f"- Concrete words instead of vague ones\n"
            f"- Direct tone, ready to send"
        )
    return (
        f"**Version améliorée**\n"
        f"{body[:1].upper() + body[1:] if body else body}\n\n"
        f"**Pourquoi c’est plus clair**\n"
        f"- Une idée par phrase\n"
        f"- Des mots concrets\n"
        f"- Ton direct, prêt à envoyer"
    )


def skill_explain(prompt: str, lang: str) -> str:
    topic = _topic(prompt, "explique", "explain", "c'est quoi", "what is", "qu'est-ce que", "define", "définis")
    if lang == "en":
        return (
            f"**{topic[:1].upper() + topic[1:]} — simple explanation**\n\n"
            f"In one line: **{topic}** is a useful idea you can understand by looking at what it does, "
            f"why it matters, and one example.\n\n"
            f"1. **What it is** — the core concept in plain words\n"
            f"2. **Why it matters** — the practical benefit\n"
            f"3. **Example** — a concrete case you can picture\n"
            f"4. **Common mistake** — what people often confuse\n\n"
            f"If you want, ask me to go deeper, give an analogy, or a quiz."
        )
    return (
        f"**{topic[:1].upper() + topic[1:]} — explication simple**\n\n"
        f"En une phrase : **{topic}** se comprend en regardant ce que c’est, à quoi ça sert, "
        f"et un exemple concret.\n\n"
        f"1. **C’est quoi** — l’idée centrale en mots simples\n"
        f"2. **À quoi ça sert** — le bénéfice pratique\n"
        f"3. **Exemple** — un cas que tu peux visualiser\n"
        f"4. **Piège fréquent** — ce que l’on confond souvent\n\n"
        f"Tu peux me demander d’approfondir, une analogie, ou un quiz."
    )


def skill_brainstorm(prompt: str, lang: str) -> str:
    topic = _topic(prompt, "brainstorm", "idées", "ideas", "idée", "donne des idées", "suggest", "suggestions")
    if lang == "en":
        ideas = [
            f"Start a short explainer about {topic}",
            f"Turn {topic} into a 3-step checklist",
            f"Create a before/after story around {topic}",
            f"Make a bold visual metaphor for {topic}",
            f"Write a FAQ (5 questions) on {topic}",
            f"Design a mini challenge people can try with {topic}",
            f"Draft a LinkedIn post + hook about {topic}",
            f"Build a comparison table: {topic} vs alternative",
        ]
        return f"**Brainstorm — {topic}**\n" + "\n".join(f"{i+1}. {x}" for i, x in enumerate(ideas))
    ideas = [
        f"Explainer court sur {topic}",
        f"Checklist en 3 étapes autour de {topic}",
        f"Histoire avant/après liée à {topic}",
        f"Métaphore visuelle forte pour {topic}",
        f"FAQ (5 questions) sur {topic}",
        f"Mini défi pratique lié à {topic}",
        f"Post LinkedIn + accroche sur {topic}",
        f"Tableau comparatif : {topic} vs alternative",
    ]
    return f"**Brainstorm — {topic}**\n" + "\n".join(f"{i+1}. {x}" for i, x in enumerate(ideas))


def skill_plan(prompt: str, lang: str) -> str:
    topic = _topic(prompt, "plan", "planning", "roadmap", "organise", "organize", "steps", "étapes", "todo")
    if lang == "en":
        return (
            f"**Plan — {topic}**\n\n"
            f"1. **Clarify the goal** — one sentence success criteria\n"
            f"2. **Break the work** — 3–5 concrete tasks\n"
            f"3. **Order** — dependencies first\n"
            f"4. **Timebox** — estimate each task\n"
            f"5. **First action today** — the smallest useful step\n"
            f"6. **Review** — what to check after delivery\n"
        )
    return (
        f"**Plan — {topic}**\n\n"
        f"1. **Clarifier l’objectif** — critère de succès en une phrase\n"
        f"2. **Découper** — 3 à 5 tâches concrètes\n"
        f"3. **Ordonner** — dépendances d’abord\n"
        f"4. **Estimer** — durée réaliste par tâche\n"
        f"5. **Action du jour** — le plus petit pas utile\n"
        f"6. **Revue** — quoi vérifier après livraison\n"
    )


def skill_pros_cons(prompt: str, lang: str) -> str:
    topic = _topic(prompt, "pour et contre", "pros and cons", "avantages", "inconvénients", "pros", "cons", "compare")
    if lang == "en":
        return (
            f"**Pros & cons — {topic}**\n\n"
            f"**Pros**\n- Speed / simplicity\n- Clear value if the goal is focused\n- Easy to explain to others\n\n"
            f"**Cons**\n- May oversimplify nuance\n- Needs good inputs\n- Risk of shallow conclusions\n\n"
            f"**Verdict**\nUse it when you need a fast decision frame, then validate with one real test."
        )
    return (
        f"**Pour & contre — {topic}**\n\n"
        f"**Pour**\n- Rapidité / simplicité\n- Valeur claire si l’objectif est net\n- Facile à expliquer\n\n"
        f"**Contre**\n- Peut trop simplifier\n- Dépend de bons inputs\n- Risque de conclusion superficielle\n\n"
        f"**Verdict**\nUtile pour décider vite, puis valider avec un vrai test."
    )


def skill_email(prompt: str, lang: str) -> str:
    topic = _topic(prompt, "email", "mail", "e-mail", "rédige un mail", "write an email", "courriel")
    if lang == "en":
        return (
            f"**Subject:** About {topic}\n\n"
            f"Hi,\n\n"
            f"I hope you’re well. I’m writing regarding {topic}. "
            f"Here’s the key point in one sentence, then the ask.\n\n"
            f"**Ask:** Could you confirm / share / approve by [date]?\n\n"
            f"Thanks,\n"
            f"[Your name]"
        )
    return (
        f"**Objet :** À propos de {topic}\n\n"
        f"Bonjour,\n\n"
        f"J’espère que tu vas bien. Je te contacte au sujet de {topic}. "
        f"Voici le point essentiel en une phrase, puis la demande.\n\n"
        f"**Demande :** Peux-tu confirmer / partager / valider d’ici [date] ?\n\n"
        f"Merci,\n"
        f"[Ton prénom]"
    )


def skill_code(prompt: str, lang: str) -> str:
    topic = _topic(prompt, "code", "programme", "python", "javascript", "js", "fonction", "function", "script")
    lower = prompt.lower()
    if "python" in lower or "py" in lower:
        snippet = (
            "```python\n"
            "def main():\n"
            f"    # TODO: {topic}\n"
            "    print('AlfAhou ready')\n\n"
            "if __name__ == '__main__':\n"
            "    main()\n"
            "```"
        )
    else:
        snippet = (
            "```javascript\n"
            "function main() {\n"
            f"  // TODO: {topic}\n"
            "  console.log('AlfAhou ready');\n"
            "}\n\n"
            "main();\n"
            "```"
        )
    if lang == "en":
        return (
            f"**Code sketch**\n{snippet}\n\n"
            f"**How to use**\n1. Replace the TODO with your logic\n2. Keep functions small\n3. Add one test case\n\n"
            f"Tell me the language and exact behavior if you want a tighter snippet."
        )
    return (
        f"**Esquisse de code**\n{snippet}\n\n"
        f"**Utilisation**\n1. Remplace le TODO par ta logique\n2. Garde des fonctions courtes\n3. Ajoute un cas de test\n\n"
        f"Précise le langage et le comportement exact pour un snippet plus serré."
    )


def skill_story(prompt: str, lang: str) -> str:
    topic = _topic(prompt, "histoire", "story", "conte", "raconte", "write a story", "poème", "poem")
    if "poem" in prompt.lower() or "poème" in prompt.lower() or "poeme" in prompt.lower():
        if lang == "en":
            return (
                f"**Poem — {topic}**\n\n"
                f"In quiet code, a spark takes flight,\n"
                f"A name — AlfAhou — turns dark to light.\n"
                f"On {topic}, thoughts align,\n"
                f"One clear sentence, then a sign."
            )
        return (
            f"**Poème — {topic}**\n\n"
            f"Dans le silence du code, une étincelle,\n"
            f"AlfAhou s’éveille, la nuit s’éclaircit.\n"
            f"Sur {topic}, les idées s’appellent,\n"
            f"Une phrase nette, puis le récit."
        )
    if lang == "en":
        return (
            f"**Short story — {topic}**\n\n"
            f"Maya opened her laptop and typed a single line about {topic}. "
            f"The screen answered like a careful friend: start small, stay clear, finish one thing. "
            f"By evening she had a draft, an image, and a plan — not perfect, but real. "
            f"That was enough to begin again tomorrow."
        )
    return (
        f"**Histoire courte — {topic}**\n\n"
        f"Maya ouvrit son ordinateur et écrivit une seule ligne sur {topic}. "
        f"L’écran répondit comme un ami prudent : commence petit, reste clair, finis une chose. "
        f"Le soir, elle avait un brouillon, une image et un plan — pas parfait, mais réel. "
        f"C’était assez pour recommencer demain."
    )


def skill_study(prompt: str, lang: str) -> str:
    topic = _topic(prompt, "cours", "fiche", "study", "réviser", "revise", "notes", "leçon", "lesson")
    if lang == "en":
        return (
            f"**Study sheet — {topic}**\n\n"
            f"**Definition** — one sentence\n"
            f"**3 key ideas**\n1. …\n2. …\n3. …\n"
            f"**Example** — one concrete case\n"
            f"**Quiz**\n- Q1: What is the core of {topic}?\n- Q2: Give one example.\n- Q3: What mistake to avoid?\n"
            f"**Tonight’s action** — explain {topic} out loud in 60 seconds."
        )
    return (
        f"**Fiche de révision — {topic}**\n\n"
        f"**Définition** — une phrase\n"
        f"**3 idées clés**\n1. …\n2. …\n3. …\n"
        f"**Exemple** — un cas concret\n"
        f"**Quiz**\n- Q1 : Quel est le cœur de {topic} ?\n- Q2 : Donne un exemple.\n- Q3 : Quelle erreur éviter ?\n"
        f"**Action du soir** — expliquer {topic} à voix haute en 60 secondes."
    )


def skill_social(prompt: str, lang: str) -> str:
    topic = _topic(prompt, "linkedin", "tweet", "post", "réseaux", "social", "caption")
    if lang == "en":
        return (
            f"**LinkedIn**\n"
            f"Hook: Most people overcomplicate {topic}.\n"
            f"Body: Here’s a simpler way — clarify the goal, ship a small version, learn fast.\n"
            f"CTA: What’s your next tiny step?\n\n"
            f"**Short caption**\n"
            f"{topic}: less theory, more shipping."
        )
    return (
        f"**LinkedIn**\n"
        f"Accroche : La plupart des gens compliquent trop {topic}.\n"
        f"Corps : Une voie plus simple — clarifier l’objectif, livrer une petite version, apprendre vite.\n"
        f"CTA : C’est quoi ton prochain micro-pas ?\n\n"
        f"**Légende courte**\n"
        f"{topic} : moins de théorie, plus de concrète."
    )


def skill_math(prompt: str, lang: str) -> str:
    expr = prompt
    m = re.search(r"(?:calcule|calculate|combien|what is|math)\s*[:\s]*(.+)$", prompt, flags=re.IGNORECASE)
    if m:
        expr = m.group(1)
    # extraire une expression
    found = re.search(r"[\d\(][\d\s+\-*/^().%]+", expr)
    raw = found.group(0) if found else expr
    result = safe_calculate(raw)
    units = convert_units(prompt)
    if result and units:
        msg = f"**Résultat** : `{raw.strip()} = {result}`\n\n**Unités** : {units}"
    elif result:
        msg = f"**Résultat** : `{raw.strip()} = {result}`"
    elif units:
        msg = f"**Conversion** : {units}"
    else:
        msg = (
            "Donne-moi une expression comme `12*7+3`, `sqrt(49)`, ou `10 km en miles`."
            if lang == "fr"
            else "Give me an expression like `12*7+3`, `sqrt(49)`, or `10 km in miles`."
        )
    return msg if lang == "fr" or not result else msg.replace("**Résultat**", "**Result**").replace("**Unités**", "**Units**").replace("**Conversion**", "**Conversion**")


def skill_time(prompt: str, lang: str) -> str:
    now = now_paris()
    if lang == "en":
        return f"**Date & time (Paris)**\n{now}"
    return f"**Date & heure (Paris)**\n{now}"


def skill_checklist(prompt: str, lang: str) -> str:
    topic = _topic(prompt, "checklist", "liste", "list", "todo", "tâches", "tasks")
    items = [
        "Clarify the outcome",
        "Gather inputs",
        "Draft v1",
        "Review / fix",
        "Ship / share",
    ] if lang == "en" else [
        "Clarifier le résultat attendu",
        "Rassembler les inputs",
        "Rédiger une v1",
        "Relire / corriger",
        "Livrer / partager",
    ]
    title = f"**Checklist — {topic}**"
    return title + "\n" + "\n".join(f"- [ ] {x}" for x in items)


def skill_swot(prompt: str, lang: str) -> str:
    topic = _topic(prompt, "swot", "forces", "faiblesses", "analyse")
    if lang == "en":
        return (
            f"**SWOT — {topic}**\n\n"
            f"**Strengths** — what already works\n"
            f"**Weaknesses** — gaps to fix\n"
            f"**Opportunities** — openings to seize\n"
            f"**Threats** — risks to watch\n\n"
            f"Next: pick one strength to amplify and one weakness to reduce this week."
        )
    return (
        f"**SWOT — {topic}**\n\n"
        f"**Forces** — ce qui marche déjà\n"
        f"**Faiblesses** — les écarts à corriger\n"
        f"**Opportunités** — les ouvertures à saisir\n"
        f"**Menaces** — les risques à surveiller\n\n"
        f"Suite : amplifier une force et réduire une faiblesse cette semaine."
    )


def skill_general(prompt: str, lang: str, mode: str, memory: dict) -> str:
    name = memory.get("name")
    chat = try_chitchat(prompt, lang, name)
    if chat:
        return chat
    return direct_answer(prompt, lang, mode, name)


SkillFn = Callable[[str, str], str]

SKILL_PATTERNS: list[tuple[str, re.Pattern[str], SkillFn]] = [
    ("translate", re.compile(r"\b(traduis|traduire|translate|traduction|en anglais|en français|in english|in french)\b", re.I), skill_translate),
    ("summarize", re.compile(r"\b(résume|resume|summarize|summary|synthèse|synthese|tl;?dr)\b", re.I), skill_summarize),
    ("rewrite", re.compile(r"\b(réécris|reecris|rewrite|améliore|ameliore|improve|reformule)\b", re.I), skill_rewrite),
    ("explain", re.compile(r"\b(explique|explain|c'?est quoi|what is|qu'?est[- ]ce que|définis|define)\b", re.I), skill_explain),
    ("brainstorm", re.compile(r"\b(brainstorm|idées|ideas|suggestions?|donne des idées)\b", re.I), skill_brainstorm),
    ("plan", re.compile(r"\b(plan|roadmap|planning|organise|organize|étapes|steps|todo)\b", re.I), skill_plan),
    ("proscons", re.compile(r"\b(pour et contre|pros and cons|avantages|inconvénients|pros|cons)\b", re.I), skill_pros_cons),
    ("email", re.compile(r"\b(email|e-?mail|mail|courriel)\b", re.I), skill_email),
    ("code", re.compile(r"\b(code|python|javascript|fonction|function|script|programme)\b", re.I), skill_code),
    ("story", re.compile(r"\b(histoire|story|conte|raconte|poème|poeme|poem)\b", re.I), skill_story),
    ("study", re.compile(r"\b(fiche|réviser|revise|study|notes|cours|leçon|lesson)\b", re.I), skill_study),
    ("social", re.compile(r"\b(linkedin|tweet|post|caption|réseaux|social)\b", re.I), skill_social),
    ("math", re.compile(r"\b(calcule|calculate|math|combien fait|sqrt|/|\*|\+|\-|\d+\s*[\+\-\*/])\b", re.I), skill_math),
    ("time", re.compile(r"\b(quelle heure|what time|date d'?aujourd|today'?s date|jour et heure)\b", re.I), skill_time),
    ("checklist", re.compile(r"\b(checklist|liste de|todo list|tâches|tasks)\b", re.I), skill_checklist),
    ("swot", re.compile(r"\b(swot|forces et faiblesses)\b", re.I), skill_swot),
]


def run_text_skill(prompt: str, lang: str, mode: str, memory: dict) -> tuple[str, str]:
    for name, pattern, fn in SKILL_PATTERNS:
        if pattern.search(prompt):
            if name in {"math", "time"}:
                return fn(prompt, lang), name
            return fn(prompt, lang), name
    return skill_general(prompt, lang, mode, memory), "general"
