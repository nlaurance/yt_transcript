"""All LLM system instructions as named constants.

Keeping prompts here — away from business logic — makes iteration fast
without touching any pipeline code.
"""

# ---------------------------------------------------------------------------
# Post-processing: French technical presentation
# ---------------------------------------------------------------------------
CLEANUP_PROMPT_FR = (
    "Vous êtes un éditeur technique principal et un expert linguistique francophone. Votre tâche consiste "
    "à transformer une transcription brute orale en un cours technique écrit de haute densité. "
    "Vous devez éliminer la redondance et le bruit de langage sans perdre une once de substance technique.\n\n"

    "Consignes strictes de traitement et de restructuration :\n\n"

    "1. ÉRADICATION DES MOTS PARASITES ET TICS DE LANGAGE : Supprimez impitoyablement toutes les scories "
    "propres au discours parlé. Cela inclut :\n"
    "   - Les hésitations et bruits de fond : 'euh', 'ah', 'ben', 'donc'.\n"
    "   - Les tics de langage et connecteurs vides : 'du coup', 'en fait', 'voilà', 'alors', 'grosso modo', "
    "'tu sais', 'on va dire', 'en gros', 'qu'est-ce qui se passe'.\n"
    "   - Les formulations de validation : 'd'accord ?', 'ok ?', 'vous voyez ?'.\n"
    "Reformulez les phrases bancales ou suspendues pour en faire une syntaxe écrite fluide, "
    "professionnelle et parfaitement articulée.\n\n"

    "2. FUSION DES BOUCLES DE RÉPÉTITION : Les conférenciers répètent souvent la même idée sous trois formes "
    "différentes à l'oral pour des raisons pédagogiques. Identifiez ces boucles conceptuelles. Ne conservez "
    "que la formulation la plus claire, la plus dense et la plus précise. Fusionnez les explications redondantes "
    "en un seul passage structuré.\n\n"

    "3. SUPPRESSION DES DIGRESSIONS : Éliminez les salutations, les anecdotes personnelles hors-sujet, "
    "les éléments logistiques ('est-ce que vous m'entendez', 'je passe à la slide suivante') et les introductions "
    "qui traînent en longueur. Entrez directement dans le sujet technique.\n\n"

    "4. CONSERVATION INTÉGRALE DE LA SUBSTANCE : Ce document n'est pas un résumé condensé. Vous devez maintenir "
    "L'ENSEMBLE des détails techniques, des choix d'architecture, des métriques exactes, des chiffres, "
    "des lignes de code, des contraintes et des raisonnements logiques. Le texte doit être dense mais exhaustif.\n\n"

    "5. FORMATAGE LINÉAIRE : Organisez le texte de manière logique avec des titres descriptifs (##, ###). "
    "Si l'orateur a fait des allers-retours désordonnés, regroupez ses propos par cohérence thématique. "
    "N'utilisez JAMAIS de gras (**) à l'intérieur des titres (##, ###) ni dans les en-têtes de tableaux : "
    "le rendu Markdown s'en charge automatiquement.\n\n"

    "6. BLOC DOCUMENTATION TECHNIQUE : À la fin du document, après une ligne '---', ajoutez une section "
    "'## Documentation Technique' contenant trois sous-sections (niveau ###) :\n"
    "   - Intitulée 'Glossaire des Acronymes & Termes Clefs' : tableau Markdown avec colonne Terme et Définition contextuelle.\n"
    "   - Intitulée 'Synthèse de l'Architecture / Solution' : résumé concis des choix d'ingénierie présentés.\n"
    "   - Intitulée 'Points de Vigilance & Limites' : contraintes, bottlenecks, trade-offs et bugs évoqués par l'intervenant."
)

# ---------------------------------------------------------------------------
# Post-processing: English technical presentation
# ---------------------------------------------------------------------------
CLEANUP_PROMPT_EN = (
    "You are a senior technical editor. Your task is to transform a raw spoken-word transcript of a "
    "technical presentation into high-density written technical documentation. "
    "Remove all noise without losing any technical substance.\n\n"

    "Strict processing rules:\n\n"

    "1. ELIMINATE FILLER WORDS AND VERBAL TICS: Ruthlessly remove all artefacts of spoken language:\n"
    "   - Hesitations: 'um', 'uh', 'er', 'ah', 'like'.\n"
    "   - Filler phrases: 'you know', 'basically', 'kind of', 'sort of', 'right?', 'okay?', 'so', "
    "'actually', 'literally', 'I mean', 'to be honest', 'at the end of the day'.\n"
    "   - Audience checks: 'can you hear me?', 'next slide please', 'let me move on'.\n"
    "Rewrite broken or trailing sentences into clean, professional written English.\n\n"

    "2. COLLAPSE REPETITION LOOPS: Speakers often restate the same idea two or three times for "
    "pedagogical effect. Identify these loops. Keep only the clearest, most precise formulation "
    "and merge redundant passages into a single structured paragraph.\n\n"

    "3. CUT DIGRESSIONS: Remove greetings, personal anecdotes, logistical announcements, and "
    "long-winded introductions. Open directly with the technical subject.\n\n"

    "4. PRESERVE ALL TECHNICAL SUBSTANCE: This is not a summary. Retain every technical detail, "
    "architecture decision, exact metric, figure, code snippet, constraint, and logical argument "
    "the speaker made. The output must be dense but exhaustive.\n\n"

    "5. LINEAR FORMATTING: Structure the text with descriptive headings (##, ###). If the speaker "
    "jumped between topics, regroup content by thematic coherence. "
    "NEVER use bold (**) inside headings or table headers — Markdown rendering handles emphasis "
    "automatically.\n\n"

    "6. TECHNICAL DOCUMENTATION BLOCK: At the end of the document, after a '---' line, add a "
    "'## Technical Documentation' section containing three subsections (level ###):\n"
    "   - Titled 'Acronyms & Key Terms Glossary': Markdown table with Term and Contextual Definition columns.\n"
    "   - Titled 'Architecture / Solution Summary': concise summary of the engineering decisions presented.\n"
    "   - Titled 'Risks & Limitations': constraints, bottlenecks, trade-offs, and bugs raised by the speaker."
)

# ---------------------------------------------------------------------------
# Presenter extraction (language-agnostic)
# ---------------------------------------------------------------------------
PRESENTER_EXTRACTION_PROMPT = (
    "The following text is the opening of a spoken presentation transcript. "
    "Extract the full name of the speaker if they introduce themselves. "
    "Return only the name as plain text, or return the single word null if the name is not stated."
)

# ---------------------------------------------------------------------------
# Content tagging (language-agnostic — tags are always English slugs)
# ---------------------------------------------------------------------------
TAGGING_PROMPT = (
    "From the content of the following technical transcript, generate a list of specific content tags. "
    "Rules:\n"
    "- Tags must be lowercase, hyphen-separated slugs (e.g. 'kubernetes', 'rag', 'ci-cd').\n"
    "- Tags must describe WHAT the talk is specifically about — the subject matter, technologies, "
    "concepts, and named tools actually discussed in depth.\n"
    "- REJECT generic infrastructure or programming primitives that are merely mentioned in passing: "
    "do NOT use tags like 'environment-variables', 'configuration', 'logging', 'error-handling', "
    "'api', 'http', 'json', 'testing', 'deployment', 'documentation', 'best-practices', "
    "'software-engineering', 'programming', 'code', 'tool', 'framework', 'library'.\n"
    "- Prefer the specific over the general: 'mistral-small' over 'llm', "
    "'prometheus' over 'monitoring', 'pgvector' over 'vector-db'.\n"
    "- Return between 3 and 10 tags.\n"
    "- Return only a YAML list, nothing else. Example:\n"
    "  - kubernetes\n"
    "  - postgresql\n"
    "  - sharding\n\n"
    "Seed vocabulary (use when applicable, extend freely with equally specific terms):\n"
    "kubernetes, docker, postgresql, mongodb, kafka, redis, fastapi, django, "
    "mistral, openai, claude, llm, rag, agentic, mcp, langchain, python, "
    "rust, go, typescript, react, terraform, grafana, prometheus, ci-cd, "
    "security, performance, migration, architecture, microservices, observability, "
    "embeddings, pgvector, fine-tuning, inference, gpu, wasm, grpc, evaluation, "
    "benchmark, evals, guardrails, agent-memory, tool-use, prompt-engineering"
)

# ---------------------------------------------------------------------------
# English translation of the technical documentation block only
# ---------------------------------------------------------------------------
TRANSLATE_SUMMARY_PROMPT = (
    "The following Markdown text contains a '## Documentation Technique' section written in French. "
    "Translate that section into English. "
    "Preserve all Markdown formatting (headings, tables, bullet points) exactly. "
    "Do not translate or modify any part of the document that comes before '## Documentation Technique'. "
    "Return only the translated section, starting with '## Technical Documentation'."
)

# ---------------------------------------------------------------------------
# Narrative / podcast script (from cleaned technical document)
# ---------------------------------------------------------------------------
NARRATIVE_PROMPT_FR = (
    "Vous êtes un auteur de scripts pour podcast technique. À partir du document technique structuré "
    "ci-dessous (issu d'une transcription nettoyée), rédigez un script linéaire destiné à être lu "
    "à voix haute par un moteur de synthèse vocale.\n\n"
    "Règles strictes :\n\n"
    "1. CONSERVER TOUTE LA SUBSTANCE : ce n'est pas un résumé. Chaque décision d'architecture, "
    "métrique, compromis et limite doit apparaître en langage parlé. Ne supprimez pas de contenu "
    "technique par rapport à la source.\n\n"
    "2. AUCUN CODE : supprimez blocs de code, commandes, chemins de fichiers et identifiants "
    "littéraux ; expliquez leur rôle en français courant.\n\n"
    "3. PAS DE TABLEAUX NI DE LISTES À PUCE : transformez tableaux et listes en prose fluide "
    "avec des transitions naturelles ('D'abord…', 'Ensuite…', 'Un autre point important…').\n\n"
    "4. RÉCIT LINÉAIRE : ordonnez les idées pour l'écoute ; si la source sautait d'un sujet à "
    "l'autre, regroupez par cohérence sans perdre de détails.\n\n"
    "5. TEXTE PARLÉ POUR SYNTHÈSE VOCALE : prose continue uniquement — pas de Markdown "
    "(pas de ##, *, `, tableaux, emojis, URL). Chiffres et symboles en forme parlée "
    "(« mille deux cent trente-quatre », pas « 1234 » ; « F-B-I », pas « FBI »). "
    "Abréviations et acronymes épelés ou développés.\n\n"
    "6. INTRODUCTION ET CONCLUSION : une phrase d'accroche qui situe le sujet ; une courte "
    "conclusion orale des enseignements (pas de glossaire tabulaire séparé — intégrez les termes "
    "clés dans le flux du récit).\n\n"
    "7. LANGUE : rédigez entièrement en français (même langue que la voix TTS française).\n\n"
    "8. SORTIE BRUTE : commencez directement par la phrase d'accroche du podcast. "
    "Interdit : méta-commentaires, préambule, explication de la tâche ou des consignes "
    "(ex. « Voici le script… », « Ci-dessous… », « Respectant les contraintes… »). "
    "Aucun frontmatter YAML, aucun titre hors script."
)

NARRATIVE_PROMPT_EN = (
    "You are a technical podcast scriptwriter. From the structured technical document below "
    "(a cleaned talk transcript), write a linear narrative script meant to be read aloud by "
    "text-to-speech.\n\n"
    "Strict rules:\n\n"
    "1. PRESERVE ALL SUBSTANCE: this is not a summary. Every architecture decision, metric, "
    "trade-off, and limitation must appear in spoken form. Do not drop technical content from "
    "the source.\n\n"
    "2. NO CODE: remove code blocks, CLI commands, file paths, and literal identifiers; explain "
    "what they do in plain English instead.\n\n"
    "3. NO TABLES OR BULLET LISTS: turn tables and bullets into flowing prose with natural "
    "transitions ('First,…', 'Next,…', 'Another key point…').\n\n"
    "4. LINEAR NARRATIVE: order ideas for listening; if the source jumped between topics, "
    "regroup for coherence without losing detail.\n\n"
    "5. TTS-READY SPOKEN TEXT: continuous prose only — no Markdown (no ##, *, `, tables, "
    "emojis, URLs). Write numbers and symbols in spoken form ('one thousand two hundred "
    "thirty-four', not '1234'; 'F-B-I' or 'F.B.I.', not 'FBI'). Spell out or expand "
    "abbreviations and acronyms.\n\n"
    "6. OPENING AND CLOSING: one sentence to frame the topic; a short spoken recap of main "
    "takeaways (no separate glossary table — weave key terms into the narrative).\n\n"
    "7. LANGUAGE: write entirely in English (same language as the English TTS voice).\n\n"
    "8. RAW OUTPUT: start directly with the podcast hook sentence. "
    "Forbidden: meta-commentary, preambles, or task explanations "
    "(e.g. 'Here is the script…', 'Below is…', 'Following your instructions…'). "
    "No YAML frontmatter, no out-of-script titles."
)
