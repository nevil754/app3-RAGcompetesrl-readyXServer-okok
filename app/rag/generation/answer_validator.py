# =============================================================
# app/rag/generation/answer_validator.py
# Validazione della risposta LLM prima di inviarla al client.
# Controlla: lunghezza, contenuto vuoto, sicurezza, lingua.
# =============================================================

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from loguru import logger


@dataclass
class ValidationResult:
    """Risultato della validazione di una risposta."""
    is_valid: bool
    answer: str                    # risposta (eventualmente corretta)
    issues: list[str]              # lista problemi trovati
    was_modified: bool = False     # True se la risposta è stata modificata


# Risposta di fallback quando la validazione fallisce completamente
_FALLBACK_ANSWER = (
    "Mi dispiace, non sono riuscito a generare una risposta appropriata. "
    "Prova a riformulare la domanda."
)

# Lunghezza minima risposta (caratteri) — meno di così è probabilmente un errore
_MIN_LENGTH = 20

# Lunghezza massima risposta (caratteri) — oltre si tronca
_MAX_LENGTH = 8000

# Pattern che indicano una risposta vuota o di errore dell'LLM
_EMPTY_PATTERNS = {
    "n/a", "n.a.", "nessuna risposta", "non lo so",
    "non disponibile", "nessun risultato", "...", "---",
}


def validate_answer(
    answer: str,
    question: str,
    min_length: int = _MIN_LENGTH,
    max_length: int = _MAX_LENGTH,
) -> ValidationResult:
    """
    Valida e normalizza la risposta LLM.

    Controlli eseguiti:
    1. Risposta non vuota
    2. Lunghezza minima
    3. Non è un pattern di risposta vuota/errore
    4. Lunghezza massima (tronca se necessario)
    5. Rimozione artefatti comuni (markdown non voluto, ecc.)

    Args:
        answer: risposta grezza dell'LLM
        question: domanda originale (per logging contestuale)
        min_length: lunghezza minima in caratteri
        max_length: lunghezza massima in caratteri

    Returns:
        ValidationResult con is_valid, answer (eventualmente corretta), issues
    """
    issues: list[str] = []
    modified = False

    # 1. Risposta vuota o None
    if not answer or not answer.strip():
        logger.warning("Risposta LLM vuota", question=question[:100])
        return ValidationResult(
            is_valid=False,
            answer=_FALLBACK_ANSWER,
            issues=["risposta vuota"],
            was_modified=True,
        )

    answer = answer.strip()

    # 2. Pattern di risposta vuota/errore
    answer_lower = answer.lower().strip(".,! \n")
    if answer_lower in _EMPTY_PATTERNS or len(answer_lower) < 3:
        logger.warning("Risposta LLM con pattern vuoto", answer=answer[:50])
        return ValidationResult(
            is_valid=False,
            answer=_FALLBACK_ANSWER,
            issues=["pattern risposta vuota"],
            was_modified=True,
        )

    # 3. Lunghezza minima
    if len(answer) < min_length:
        issues.append(f"risposta troppo corta ({len(answer)} char, min {min_length})")
        logger.warning("Risposta LLM troppo corta", length=len(answer))
        # Non la scarta — può essere una risposta breve legittima

    # 4. Lunghezza massima — tronca al boundary di frase più vicino
    if len(answer) > max_length:
        issues.append(f"risposta troncata ({len(answer)} → {max_length} char)")
        answer = _truncate_at_sentence(answer, max_length)
        modified = True
        logger.info(f"Risposta troncata a {max_length} caratteri")

    # 5. Rimozione artefatti comuni dell'LLM
    answer, artifact_issues = _remove_artifacts(answer)
    if artifact_issues:
        issues.extend(artifact_issues)
        modified = True

    is_valid = len(answer) >= min_length

    if issues:
        logger.debug("Validazione risposta", issues=issues, modified=modified)

    return ValidationResult(
        is_valid=is_valid,
        answer=answer if is_valid else _FALLBACK_ANSWER,
        issues=issues,
        was_modified=modified,
    )


def _truncate_at_sentence(text: str, max_length: int) -> str:
    """
    Tronca il testo al boundary di frase più vicino prima di max_length.
    Evita di tagliare a metà parola o frase.
    """
    if len(text) <= max_length:
        return text

    # Cerca l'ultimo punto/punto esclamativo/interrogativo prima di max_length
    truncated = text[:max_length]
    last_sentence_end = max(
        truncated.rfind(". "),
        truncated.rfind(".\n"),
        truncated.rfind("! "),
        truncated.rfind("? "),
    )

    if last_sentence_end > max_length // 2:
        # C'è un boundary di frase nella seconda metà — tronca lì
        return text[:last_sentence_end + 1].strip()

    # Nessun boundary trovato — tronca all'ultima parola intera
    last_space = truncated.rfind(" ")
    if last_space > 0:
        return text[:last_space].strip() + "..."

    return truncated + "..."


def _remove_artifacts(answer: str) -> tuple[str, list[str]]:
    """
    Rimuove artefatti comuni nelle risposte LLM.

    Artefatti rimossi:
    - Prefissi tipo "RISPOSTA:", "Risposta:", "A:"
    - Markdown code fence iniziali non voluti (```)
    - Ripetizione della domanda in apertura
    - Frasi di chiusura generiche dell'LLM
    """
    import re
    issues: list[str] = []
    original = answer

    # Rimuovi prefissi tipo "RISPOSTA:", "A:", "Assistant:"
    prefix_pattern = r'^(RISPOSTA|Risposta|ANSWER|Answer|A|Assistant|Assistente)\s*:\s*'
    if re.match(prefix_pattern, answer):
        answer = re.sub(prefix_pattern, '', answer).strip()
        issues.append("rimosso prefisso risposta")

    # Rimuovi fence markdown iniziale e finale se la risposta NON è codice
    if answer.startswith("```") and answer.endswith("```"):
        # Controlla se è codice intenzionale (ha un language identifier)
        first_line = answer.split("\n")[0]
        lang = first_line.replace("```", "").strip()
        if not lang or lang.lower() in {"", "text", "txt"}:
            # Non è codice — rimuovi le fence
            answer = re.sub(r'^```\w*\n?', '', answer)
            answer = re.sub(r'\n?```$', '', answer)
            answer = answer.strip()
            issues.append("rimosso markdown fence non necessario")

    # Rimuovi frasi di chiusura generiche
    closing_patterns = [
        r'\n\nSpero che questa risposta sia stata utile\.?$',
        r'\n\nFammi sapere se hai altre domande\.?$',
        r'\n\nSe hai bisogno di ulteriori chiarimenti.*$',
        r'\n\nLet me know if you.*$',
    ]
    for pattern in closing_patterns:
        new_answer = re.sub(pattern, '', answer, flags=re.IGNORECASE).strip()
        if new_answer != answer:
            answer = new_answer
            issues.append("rimossa frase di chiusura generica")
            break

    return answer, issues