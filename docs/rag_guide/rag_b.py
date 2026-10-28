from lib import bullets, chain, chapter, files, flow, functions, h2, kpis, md, note, p, pre, qa, ref, table

BE, FE, AS = "backend/app/", "frontend/src/", "backend/app/services/assistant/"


def build() -> list[str]:
    out = []

    out.append(chapter("4", "The pipeline, end to end", "c4", "From the send button to the 'Based on' line, with the file and line for every step.", (
        chain(["Browser", "Route: rate limit, own chat", "Safety rules", "Plan", "Retrieve", "Generate", "Verify", "Store", "Show sources"])
        + flow([
            ("Browser", "'Send' posts the question and the current chat id.", FE + "pages/Assistant.tsx", "const out = await askAssistant(content, activeId)"),
            ("Router", "Rate limit of 20 questions a minute per user, then the chat is loaded and checked to belong to the user.", BE + "api/routes/assistant.py", "limit = get_settings().ASSISTANT_QUESTIONS_PER_MINUTE"),
            ("Service", "The question is stored; the last 6 messages become the history; the previous query (for a follow-up like 'and last month?') is read from the stored answer.", AS + "__init__.py", "history = [(m.role.value, m.content)"),
            ("Service", "**Safety rules first**: emergency words, greetings or help, and (for citizens) diagnosis or medicine questions. These never reach Gemini.", AS + "__init__.py", "if router.EMERGENCY.search(question):"),
            ("Model", "**Plan**: Gemini is given only the role's queries as functions (automatic calling disabled, temperature 0) and may choose up to three.", AS + "llm.py", "async def choose_tools"),
            ("Service", "Each chosen name must be in the role's list; arguments are cleaned exactly like the rule-based router's.", AS + "__init__.py", "args = {k: p.clean(raw.get(k)) for k, p in tool.params.items()}"),
            ("Service", "If Gemini is off, fails or returns nothing, the keyword router scores every allowed query; failing that, a follow-up reuses the previous query; failing that, **no query** and a polite refusal.", AS + "router.py", "def plan"),
            ("Service", "A worker with no centre gets the 'not linked' message instead of an empty answer.", AS + "__init__.py", "tool.needs_facility"),
            ("Database", "Each query runs in a **read-only** transaction with a 5 s limit; `:me`, `:phc_id` and `:district` come from the signed-in user.", AS + "__init__.py", "async def retrieve"),
            ("Service", "Empty results get an honest sentence ('none of your readings were flagged'); too little history for a comparison says so.", AS + "__init__.py", "def _empty"),
            ("Model", "**Generate**: Gemini receives the question and the rows as JSON (whole rows only, within a 12,000-character budget, times already in India time) and must answer from them.", AS + "llm.py", "async def write_answer"),
            ("Service", "**Verify**: every number in the answer must appear in the rows, the question or the parameters; otherwise the answer is discarded and the template answer is used.", AS + "__init__.py", "missing = grounding.unsupported("),
            ("Service", "The template (no Gemini) turns the same rows into plain sentences, so there is always an answer.", AS + "compose.py", "def compose"),
            ("Database", "The question and answer are stored with the SQL that ran, the sources, the number of rows, whether the numbers were checked, the latency and the tokens used.", AS + "__init__.py", "answer = ChatMessage("),
            ("Browser", "The bubble shows 'Based on: …' (query, period, rows) and a 'Numbers checked' badge; one click opens the rows.", FE + "pages/Assistant.tsx", "function Sources"),
        ])
        + h2("4.1 The possible outcomes")
        + table(["Outcome", "When", "Engine label stored"], [
            ["Answer by Gemini", "A query matched, rows came back and all numbers are in the rows", "`gemini`"],
            ["Answer by the template", "Gemini is off, failed (for example a quota error) or timed out", "`rules` or `gemini+template`"],
            ["Template instead of Gemini", "Gemini's answer contained a number not in the rows", "`gemini, replaced by template`"],
            ["Empty answer", "The query ran and returned no rows", "`gemini` or `rules`"],
            ["Refusal: out of scope", "No query fits the question", "none"],
            ["Refusal: medical advice", "A citizen asked for a diagnosis or medicine advice", "none"],
            ["Emergency reply", "Emergency words: 'call 108 now'", "none"],
        ])
        + h2("4.2 Follow-ups and several questions in one")
        + bullets([
            "**Follow-up:** 'and over the last 90 days?' reuses the previous query with the new window, but only if the new text changes a parameter that query takes (`router.follow_up`).",
            "**Several parts:** 'my latest blood pressure and any advisories for my area' lets Gemini choose two queries; the answer covers both and the sources line lists both.",
        ])
        + h2("4.3 Failure handling")
        + table(["What fails", "What happens"], [
            ["Gemini rate limit (free tier: 5 requests a minute)", "The call fails over to the next configured key; with none left the rule-based router and the template answer take over"],
            ["Gemini does not answer within 20 s on a key", "Same fallback"],
            ["Gemini's answer has a number not in the rows", "Discarded; template used; logged as a grounding failure"],
            ["The database query fails or times out", "'I couldn't read your records just now', stored as an error"],
            ["The user asks too fast", "429 'wait 60 seconds'"],
        ])
        + files([
            (BE + "api/routes/assistant.py", "async def ask", "The route."),
            (AS + "__init__.py", "async def ask", "Stores the question, calls `_answer`, stores the answer."),
            (AS + "llm.py", "async def _generate", "Tries each Gemini key in turn with a 20 s limit."),
            (AS + "router.py", "def follow_up", "Reuses the previous query for 'and last month?'."),
        ])
    )))

    out.append(chapter("5", "Defending the name 'RAG'", "c5", "RAG is a pattern, not a product. This chapter is the argument, the evidence to show, and the answers to the hostile questions.", (
        h2("5.1 The definition")
        + p("**Retrieval-Augmented Generation** (Lewis et al., 2020) means three things: **(1)** the model is given knowledge it does not have, **(2)** that knowledge is **retrieved at question time**, chosen for each question, and **(3)** the answer is **generated from what was retrieved**. The definition says nothing about *how* retrieval works. Vector search is one retriever; keyword search, SQL, knowledge graphs and API calls are others. Using SQL over structured data is called **structured RAG** or SQL-grounded RAG.")
        + table(["The three tests", "Nira", "Evidence (open it)"], [
            ["Knowledge the model does not have", "Yes: each citizen's readings, flags and visits are private and are not in Gemini's training data", ref(AS + "catalog.py", "TOOLS: tuple")],
            ["Retrieved at question time, per question", "Yes: the planner picks a different query and parameters for each question", ref(AS + "llm.py", "async def choose_tools")],
            ["Generated from the retrieved data and checked against it", "Yes: the answer prompt allows only the rows, and a number check enforces it", ref(AS + "grounding.py", "def unsupported")],
        ])
        + h2("5.2 'It is just an API call to Gemini'")
        + table(["", "A plain LLM API call", "Nira"], [
            ["What the model sees", "Only the question", "The question **and the rows retrieved for this user**"],
            ["Where the facts come from", "The model's training data (it may guess)", "The database, fetched by a vetted query"],
            ["Can it answer 'what was my average systolic last month'?", "No: it has never seen your readings", "Yes: `AVG` over this user's rows"],
            ["Who limits what is visible", "Nobody", "The server: scope binds, role list, read-only, row and time limits"],
            ["Can the answer be checked?", "No", "Yes: every number is checked against the rows and the sources are stored"],
            ["Our code before and between the model calls", "none", "Safety rules, parameter cleaning, read-only retrieval of this user's rows"],
            ["Our code after the model", "none", "Number verification, template fallback, storage"],
        ])
        + note("**The line to use:** *the language model does two of the six steps: it chooses the query and it words the answer. Our code runs the safety rules before them, the retrieval between them and the number check after them. Every RAG system calls a model API; what makes it RAG is the retrieval that feeds the model and the grounding that follows it.*", "key")
        + h2("5.3 'Where are the vector database and the embeddings?'")
        + p("There are none, on purpose, because **the data is structured and the questions need exact answers**:")
        + table(["Question", "What it needs", "Similarity search"], [
            ["Average systolic over 30 days", "`AVG` over rows in a date range", "Cannot compute; returns text that is merely similar"],
            ["Readings above 140 this week", "A numeric filter and a count", "Cannot filter by value; may miss rows"],
            ["Who has a critical flag right now", "An exact, current, filtered list", "Index would be stale within minutes"],
            ["Only my own data", "A hard `user_id = :me` rule", "Ranks by closeness; no notion of who may see what"],
            ["Show me where this answer came from", "The exact rows", "A list of text chunks"],
        ])
        + bullets([
            "A health record row such as `systolic 142, 2026-10-12` gains nothing from embedding: there is no meaning to find, only numbers to filter, count and average.",
            "**Safety:** a missed row in a health answer is dangerous. SQL returns every matching row; similarity returns the top few.",
            "**Freshness:** readings arrive every few hours; re-embedding would always lag. SQL is always current.",
            "**Access control:** per-user isolation is one bound parameter in SQL and an awkward filter in a vector index.",
            "**Cost and complexity:** no embedding model, no vector store to run, secure and back up; the data already lives in PostgreSQL.",
        ])
        + h2("5.4 Why the model does not write the SQL")
        + p("The common alternative is **text-to-SQL**, where the model writes the query. It is flexible but risky: a clever prompt could write a different `WHERE` clause or a cross-patient join. Nira's model only picks from **vetted, parameterised queries**, which is the safe form of the same idea. That is why it is described as tool-based retrieval, not text-to-SQL.")
        + h2("5.5 What a vector database would add, and where")
        + bullets([
            "**Unstructured text:** clinical guidelines, health FAQs, advisory messages and free-text notes. 'What should I do for a fever lasting two days?' is a meaning question, and similarity search is the right retriever for it.",
            "**How it would plug in:** one new entry in the menu, `search_guidelines`, whose retriever is a `pgvector` search inside the same PostgreSQL. Planning, scope, verification and storage do not change. That is **hybrid RAG**, and the tool menu is already shaped for it.",
            "**It is deliberately not built yet:** the assistant refuses medical-advice questions, so there is no guideline corpus to retrieve from.",
        ])
        + h2("5.6 The name to use")
        + table(["Say", "Do not say"], [
            ["**SQL-grounded RAG with tool-based retrieval** (structured RAG)", "'RAG with a vector store'"],
            ["'Retrieval is parameterised SQL chosen by function calling'", "'text-to-SQL' (the model does not write SQL)"],
            ["'The language model plans and words; the database decides what is true'", "'a chatbot connected to a database'"],
        ])
        + h2("5.7 The one-minute spoken answer")
        + p("*'RAG means retrieving knowledge at question time and generating from it. Our knowledge is each person's health records, which are private, structured and change every day, so the right retriever is parameterised SQL, not similarity search. The language model plans which vetted query to run and then words the result; the server fetches the rows with the user's identity bound, read-only, and a number check rejects any answer whose figures are not in the rows. A vector database would be the right tool for guideline text, and the design lets us add it as one more tool.'*")
        + h2("5.8 What to show if asked to prove it")
        + bullets([
            "Open any answer's **Based on** line, then expand it: the exact query, parameters and rows. That is the retrieved context.",
            f"Open {ref(AS + 'catalog.py', 'TOOLS: tuple')} (the menu), {ref(AS + 'llm.py', 'ANSWER_PROMPT')} (the grounding instruction) and {ref(AS + 'grounding.py', 'def unsupported')} (the check).",
            "Ask the same question as a citizen and as a worker: different queries, different rows.",
            "Ask 'what is the capital of France?': a refusal, because no query fits.",
        ])
        + qa([
            ("Isn't this just calling the Gemini API?", "Gemini does two of the six steps: it chooses the query and it words the answer. Between them the server fetches this user's rows with a vetted query; after them a check rejects any number not in those rows. Without the retrieval Gemini could not answer at all, because it has never seen the data."),
            ("Where are the embeddings?", "There are none, because every question is about exact values, counts and dates in structured rows. Embeddings find similar text; they cannot average, filter or enforce who may see what. For guideline text I would add a vector tool."),
            ("So it is a rule-based bot with an LLM on top?", "The menu of queries is the safety boundary, and it is fixed on purpose. The choice among them and the wording of the answer are done by the language model, which is how function-calling RAG is normally built. There is also a keyword planner as a fallback when the model is unavailable."),
            ("How do you know the model did not make up a number?", "Every number in the answer is extracted and must appear in the rows, the question or the parameters. If one does not, the answer is thrown away and a template answer is shown. The result of the check is stored and shown as 'Numbers checked'."),
            ("What if someone types an instruction inside their own data?", "The answer prompt tells the model that the rows are data, not instructions, and the model has no tool that can change anything: every query is read-only."),
            ("What does 'retrieval' mean when there is no search?", "Retrieval means selecting the relevant knowledge for this question. Choosing the right query and parameters from a menu, then running it, is exactly that selection."),
        ])
    )))
    return out
