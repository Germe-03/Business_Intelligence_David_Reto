"""KI-Agent: Natural Language -> sichere BI-Auswertung -> Antwort.

Statt LangChain wird hier ein schlanker, transparenter Zweistufen-Ansatz
verwendet:
1. LLM generiert eine SQL-Abfrage gegen das bekannte Schema.
2. SQL wird sanity-gecheckt (nur SELECT, kein DDL/DML) und in DuckDB
   ausgeführt.
3. LLM formuliert die Antwort in Deutsch auf Basis des Result-Frames.

User wählt im Sidebar den Provider (OpenAI oder Anthropic) und gibt seinen
API-Key ein. Keys werden nur im Streamlit-Session-State gehalten, nicht
gespeichert.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Iterable

import pandas as pd
import streamlit as st

from dashboard.bi.data_layer import get_connection, schema_overview


SYSTEM_PROMPT = """Du bist ein deutschsprachiger BI-Analyst.
Du arbeitest mit einer DuckDB, die Views über einen Flughafen-Datendump bereitstellt.
Es ist eine generische Demo-Flugdatenbank mit rund 13'500 Flughäfen weltweit, nicht nur Zürich
(Zürich = airport_id 13591, aber nur rund 52 Abflüge ab ZRH im Dump - keine ausgeprägte Hub-Struktur).
Datenstand: Flüge und Buchungen aus Sommer 2015 (Juni-September); weatherdata reicht von 2005 bis 2015.
Die Daten enthalten Flüge, Buchungen, Passagiere und Wetter.

SCHEMA:
{schema}

REGELN:
- Antworte mit GENAU EINER SQL-Abfrage (nur SELECT/WITH), keine DDL/DML.
- Verwende ausschliesslich die Tabellen aus dem Schema. Keine erfundenen Spalten.
- Limit ergebnisse auf <=200 Zeilen, ausser der Nutzer fragt explizit nach mehr.
- Datum/Zeit-Spalten haben den passenden Typ; verwende DATE_TRUNC, EXTRACT, AGE.
- 'from' und 'to' wurden zu 'from_id' und 'to_id' umbenannt (Reserved Words).
- Wenn die Frage Statistiken pro Airline/Aircraft braucht: JOIN über airline_id bzw type_id.
- 'flight_log' ist im Dump leer (0 Zeilen). Hinweise dazu erwähnen, nicht queryen.
- Gib keine technischen Schlüsselspalten wie *_id, from_id oder to_id im SELECT aus.

OUTPUT-FORMAT:
Antworte exakt im folgenden JSON-Format, ohne weitere Erklärungen:
{{"sql": "...", "explanation": "kurzer Hinweis, was abgefragt wird"}}
"""


ANSWER_PROMPT = """Du bist BI-Analyst. Der User hat gefragt: {question}

Ergebnis der Abfrage (max. 20 Zeilen als Vorschau):
{result_preview}

Erkläre das Ergebnis in 3-6 Sätzen auf Deutsch (de-CH). Nenne konkrete Zahlen.
Wenn das Ergebnis leer ist, schreibe das klar."""


TECHNICAL_COLUMNS = {
    "id",
    "airport_id",
    "airline_id",
    "airplane_id",
    "booking_id",
    "flight_id",
    "from_id",
    "passenger_id",
    "type_id",
    "to_id",
}

DISPLAY_LABELS = {
    "aircraft_type": "Flugzeugtyp",
    "airline": "Airline",
    "airlinename": "Airline",
    "avg_age": "Durchschnittsalter",
    "avg_price": "Ticketpreis im Schnitt (CHF)",
    "bookings": "Buchungen",
    "capacity": "Sitzplätze",
    "country": "Land",
    "day": "Datum",
    "dest": "Destination",
    "flightno": "Flugnummer",
    "flights": "Flüge",
    "iata": "IATA",
    "revenue": "Umsatz (CHF)",
}


@dataclass(frozen=True)
class LLMResult:
    sql: str
    explanation: str


def _schema_block() -> str:
    overview = schema_overview()
    parts = []
    for table, cols in overview.items():
        parts.append(f"- {table}({', '.join(cols)})")
    return "\n".join(parts)


def _sanitize_sql(sql: str) -> str:
    sql = sql.strip().rstrip(";")
    forbidden = re.compile(
        r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|ATTACH|COPY|EXPORT|PRAGMA|SET)\b",
        re.IGNORECASE,
    )
    if forbidden.search(sql):
        raise ValueError("Nur SELECT/WITH-Queries erlaubt.")
    if not re.match(r"^\s*(WITH|SELECT)\b", sql, re.IGNORECASE):
        raise ValueError("SQL muss mit SELECT oder WITH beginnen.")
    return sql


def _extract_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*", "", text).strip()
        text = text.rstrip("`").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def call_openai(api_key: str, model: str, messages: list[dict]) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0,
    )
    return resp.choices[0].message.content or ""


def call_anthropic(api_key: str, model: str, messages: list[dict]) -> str:
    from anthropic import Anthropic

    client = Anthropic(api_key=api_key)
    system = next((m["content"] for m in messages if m["role"] == "system"), "")
    convo = [m for m in messages if m["role"] != "system"]
    resp = client.messages.create(
        model=model,
        system=system,
        messages=convo,
        max_tokens=2048,
        temperature=0,
    )
    return "".join(block.text for block in resp.content if getattr(block, "type", "") == "text")


def generate_sql(provider: str, api_key: str, model: str, question: str,
                 history: Iterable[dict]) -> LLMResult:
    system = SYSTEM_PROMPT.format(schema=_schema_block())
    messages = [{"role": "system", "content": system}]
    for msg in history:
        if msg["role"] in ("user", "assistant"):
            messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": question})

    if provider == "OpenAI":
        raw = call_openai(api_key, model, messages)
    else:
        raw = call_anthropic(api_key, model, messages)

    data = _extract_json(raw)
    sql = _sanitize_sql(str(data.get("sql", "")))
    explanation = str(data.get("explanation", "")).strip()
    return LLMResult(sql=sql, explanation=explanation)


def explain_result(provider: str, api_key: str, model: str, question: str,
                   result: pd.DataFrame) -> str:
    display_result = _display_dataframe(result)
    preview = display_result.head(20).to_markdown(index=False) if not display_result.empty else "(leer)"
    prompt = ANSWER_PROMPT.format(question=question, result_preview=preview)
    messages = [{"role": "user", "content": prompt}]
    if provider == "OpenAI":
        return call_openai(api_key, model, messages)
    return call_anthropic(api_key, model, messages)


def run_sql(sql: str) -> pd.DataFrame:
    con = get_connection()
    return con.execute(sql).df()


def _display_dataframe(result: pd.DataFrame) -> pd.DataFrame:
    if result.empty:
        return result
    visible_columns = [
        column for column in result.columns
        if not _is_technical_column(str(column))
    ]
    display = result.loc[:, visible_columns].copy()
    return display.rename(columns={
        column: DISPLAY_LABELS.get(str(column).lower(), str(column).replace("_", " ").title())
        for column in display.columns
    })


def _is_technical_column(column: str) -> bool:
    lowered = column.lower()
    return lowered in TECHNICAL_COLUMNS or lowered.endswith("_id")


def render_ai_agent() -> None:
    st.title("KI-Datenanalyst")
    st.caption(
        "Frag in natürlicher Sprache. Die Auswertung wird nur lesend berechnet"
        " und als verständliche Antwort mit Tabelle gezeigt."
    )

    st.sidebar.subheader("KI-Konfiguration")
    provider = st.sidebar.selectbox("Provider", ["OpenAI", "Anthropic"], index=0)
    if provider == "OpenAI":
        default_model = "gpt-4o-mini"
        models = ["gpt-4o", "gpt-4o-mini", "gpt-4.1-mini"]
    else:
        default_model = "claude-haiku-4-5-20251001"
        models = [
            "claude-haiku-4-5-20251001",
            "claude-sonnet-4-6",
            "claude-opus-4-7",
        ]
    model = st.sidebar.selectbox("Modell", models, index=models.index(default_model))
    api_key = st.sidebar.text_input(
        f"{provider} API-Key", type="password",
        help="Wird nur im Session-Speicher gehalten.",
    )
    st.sidebar.caption("Hinweis: Keys werden nicht persistiert.")
    if st.sidebar.button("Verlauf zurücksetzen", use_container_width=True):
        st.session_state.ai_messages = []
        st.session_state.pop("pending_question", None)
        st.rerun()

    if "ai_messages" not in st.session_state:
        st.session_state.ai_messages = []

    sample_questions = [
        "Top 5 Routen ab Zürich nach Umsatz im August 2015",
        "Welche Wetterlage hatte den höchsten Durchschnittswind?",
        "Wie viele Buchungen pro Tag im Juli 2015?",
        "Top 10 Airlines nach Sitzangebot",
    ]
    chips = st.columns(len(sample_questions))
    for col, q in zip(chips, sample_questions):
        if col.button(q, use_container_width=True):
            st.session_state.pending_question = q

    for msg in st.session_state.ai_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["role"] == "assistant" and msg.get("dataframe") is not None:
                display_df = _display_dataframe(msg["dataframe"])
                if display_df.empty and not msg["dataframe"].empty:
                    st.info("Das Ergebnis enthält nur technische Schlüssel und wird daher nicht angezeigt.")
                else:
                    st.dataframe(display_df, use_container_width=True, hide_index=True)

    placeholder = "z.B. Welche 5 Destinationen ab ZRH bringen den meisten Umsatz?"
    submitted = st.chat_input(placeholder)
    pending = st.session_state.pop("pending_question", None)
    question = submitted or pending

    if not question:
        return

    if not api_key:
        st.warning(f"Bitte links den {provider}-API-Key eintragen, um die Frage auszuwerten.")
        return

    st.session_state.ai_messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Bereite Auswertung vor ..."):
            try:
                llm = generate_sql(provider, api_key, model, question,
                                   st.session_state.ai_messages[:-1])
            except Exception as exc:
                error_text = (
                    "Die Frage konnte nicht sicher in eine Auswertung übersetzt werden. "
                    "Bitte formuliere sie konkreter, z.B. mit Datum, Kennzahl oder Airline."
                )
                st.error(error_text)
                st.session_state.ai_messages.append({
                    "role": "assistant",
                    "content": error_text,
                })
                return

        st.markdown(f"**Vorgehen:** {llm.explanation or 'Auswertung berechnen ...'}")

        try:
            result = run_sql(llm.sql)
        except Exception as exc:
            error_text = (
                "Die Auswertung konnte so nicht berechnet werden. "
                "Bitte frage nach einer klaren Kennzahl, einem Zeitraum oder einer Gruppierung."
            )
            st.error(error_text)
            st.session_state.ai_messages.append({
                "role": "assistant",
                "content": error_text,
            })
            return

        display_result = _display_dataframe(result)
        if display_result.empty and not result.empty:
            st.info("Das Ergebnis enthält nur technische Schlüssel und wird daher nicht angezeigt.")
        else:
            st.dataframe(display_result, use_container_width=True, hide_index=True)
        with st.spinner("Antwort formulieren ..."):
            try:
                answer = explain_result(provider, api_key, model, question, result)
            except Exception as exc:
                answer = (
                    "Ergebnis siehe Tabelle. Die automatische Erklärung ist im Moment nicht verfügbar."
                )
        st.markdown(answer)
        st.session_state.ai_messages.append({
            "role": "assistant",
            "content": answer,
            "dataframe": result,
        })
