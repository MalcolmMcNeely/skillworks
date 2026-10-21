# Words are matched by string and never by a judge, so a word score holds on every run and a synonym is never a find.

import re
from typing import NamedTuple

import blind_clone
from context_backfill.answer_sheet import WORD, bold_name, read_sheet
from context_backfill.context_map import MAP_FILE, contexts_of

HEADWORD = re.compile(r"^\*\*(.+?)\*\*:")
AVOID = "_Avoid_:"

# The glossary rule turns down a general programming concept, so a headword on this list breaks it.
GENERAL = frozenset(word.casefold() for word in (
    "cache", "callback", "class", "client", "component", "config", "configuration", "controller", "data",
    "error", "event", "exception", "factory", "function", "handler", "helper", "info", "interface", "item",
    "list", "manager", "message", "method", "model", "module", "object", "process", "processor", "provider",
    "queue", "request", "response", "result", "retry", "server", "service", "state", "status", "string",
    "thread", "timeout", "type", "util", "utility", "value", "wrapper"))


class Glossary(NamedTuple):
    context: str
    headwords: dict
    losing: dict


class Drafted(NamedTuple):
    name: str
    context: str
    headword: str
    avoids: set


def avoided(line):
    return [word for word in (part.strip().strip("`").rstrip(".").strip() for part in line[len(AVOID):].split(","))
            if word]


def glossary_of(context, said):
    headwords, losing, last = {}, {}, None
    for line in said.splitlines():
        found = HEADWORD.match(line)
        if found:
            last = found.group(1).strip()
            headwords[last.casefold()] = last
        elif line.startswith(AVOID) and last:
            losing.update((word.casefold(), last) for word in avoided(line))
    return Glossary(context, headwords, losing)


def glossaries(runner, source, pin):
    named = contexts_of(blind_clone.shown(runner, source, pin, MAP_FILE) or "")
    return [glossary_of(context, blind_clone.shown(runner, source, pin, path) or "")
            for context, path in named.items()]


def drafted(sheet):
    return [Drafted(entry.name, entry.context.strip(), bold_name(entry.text, entry.title),
                    {word.casefold() for line in entry.text.splitlines() if line.startswith(AVOID)
                     for word in avoided(line)})
            for entry in read_sheet(sheet).entries if entry.is_draft and entry.letter == WORD]


def ere_escaped(char):
    if char.isalpha():
        return "[{}{}]".format(char.lower(), char.upper())
    return "\\" + char if char in "\\.[](){}*+?|^$" else char


# Joined and bounded as the words rule matches a name, so EventLog and event_log are both evidence of Event log.
def pickaxe_pattern(word):
    joined = "[ _-]?".join("".join(ere_escaped(char) for char in part) for part in word.split())
    return "(^|[^A-Za-z0-9])" + joined + "([^a-z0-9]|$)"


def evidenced(runner, clone, glossary):
    return {word for word in glossary.losing
            if blind_clone.must(blind_clone.git(runner, clone, "log", "-G", pickaxe_pattern(word), "--format=%h",
                                                "-1", "HEAD"), "search the Blind clone's history").strip()}


def of_glossary(drafts, glossary):
    return [draft for draft in drafts if draft.context.casefold() == glossary.context.casefold()]


def found(drafts, glossary):
    return {draft.headword.casefold() for draft in of_glossary(drafts, glossary)} & set(glossary.headwords)


# A word that is a headword of its own is found under its own name, even where another entry turned it down.
def under_losing_names(drafts, glossary):
    return [(draft, glossary.losing[draft.headword.casefold()]) for draft in of_glossary(drafts, glossary)
            if draft.headword.casefold() in glossary.losing and draft.headword.casefold() not in glossary.headwords]


def general(drafts):
    return [draft for draft in drafts if draft.headword.casefold() in GENERAL]


def avoids_found(drafts, glossary, evidence):
    return sum(1 for word in evidence if any(
        draft.headword.casefold() == glossary.losing[word].casefold() and word in draft.avoids
        for draft in of_glossary(drafts, glossary)))
