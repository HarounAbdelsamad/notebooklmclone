"""Prompt templates for the RAG pipeline, chat memory, and generated outputs."""

from app.services.llm import Message

# --------------------------------------------------------------------------- answering

ANSWER_SYSTEM = (
    "You are a helpful research assistant answering questions strictly from the provided "
    "sources. Rules:\n"
    "- Use ONLY the numbered sources below. Do not use outside knowledge.\n"
    "- Cite every claim with bracketed markers like [1] or [2][3] referencing the source "
    "numbers you used.\n"
    "- If the sources do not contain the answer, say so plainly instead of guessing.\n"
    "- Be concise and well-structured."
)


def _format_sources(chunks: list[tuple[int, str]]) -> str:
    return "\n\n".join(f"[{n}] {text}" for n, text in chunks)


def build_answer_messages(
    question: str,
    numbered_sources: list[tuple[int, str]],
    memory_block: str = "",
) -> list[Message]:
    context = _format_sources(numbered_sources) if numbered_sources else "(no sources found)"
    user = ""
    if memory_block:
        user += f"Conversation context:\n{memory_block}\n\n"
    user += f"Sources:\n{context}\n\nQuestion: {question}"
    return [
        {"role": "system", "content": ANSWER_SYSTEM},
        {"role": "user", "content": user},
    ]


# --------------------------------------------------------------------------- query rewrite

REWRITE_SYSTEM = (
    "Rewrite the user's latest question into a single standalone search query that captures "
    "its full intent using the conversation context. Output only the rewritten query text."
)


def build_rewrite_messages(recent_turns: str, question: str) -> list[Message]:
    content = (
        f"Conversation so far:\n{recent_turns}\n\n"
        f"Latest question: {question}\n\nStandalone search query:"
    )
    return [
        {"role": "system", "content": REWRITE_SYSTEM},
        {"role": "user", "content": content},
    ]


# --------------------------------------------------------------------------- memory jobs

SUMMARIZE_SYSTEM = (
    "Summarize the following conversation into a compact paragraph capturing decisions, topics, "
    "and open threads. Preserve information useful for continuing the conversation."
)

EXTRACT_FACTS_SYSTEM = (
    "Extract durable, user-specific facts worth remembering long-term from the conversation "
    "(preferences, goals, entities, constraints). Return one fact per line, or nothing if none."
)


# --------------------------------------------------------------------------- generated outputs

OUTPUT_SYSTEM = {
    "summary": "Write a clear, well-structured summary of the provided sources.",
    "faq": "Produce a FAQ (Q&A pairs) covering the key points in the provided sources.",
    "study_guide": (
        "Create a study guide with key concepts, definitions, and review questions from the "
        "provided sources."
    ),
    "briefing": (
        "Write an executive briefing document highlighting the essentials from the sources."
    ),
    "timeline": "Extract a chronological timeline of events/points from the provided sources.",
}


def build_output_messages(output_type: str, sources_text: str) -> list[Message]:
    system = OUTPUT_SYSTEM.get(output_type, OUTPUT_SYSTEM["summary"])
    return [
        {"role": "system", "content": system + " Ground everything in the sources; be faithful."},
        {"role": "user", "content": f"Sources:\n{sources_text}"},
    ]
