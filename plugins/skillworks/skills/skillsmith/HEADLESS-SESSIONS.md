# Sessions nobody watches

What holds when the document will run in a Session that a script starts with `claude -p`: a skill that is a step of a loop, or the prompt the script sends. The writing rules are in `SKILL.md` beside this file.

The Session ends when the turn ends, and a document cannot make it finish. The script has to check that the work was done.

## Nobody can be asked

- The question tool is not offered under `claude -p`. So a question is only the text of a last message, and the turn ends on it. Such an ending often reads as two options and a pick, with no question mark.
- A skill that both a person and a script start is written for the person. Its asks stay, because a person is there to answer. Where the two runs differ, the skill says which run a rule is for.
- The paragraph that says nobody is watching belongs in the script's prompt, once, and not in each skill. It has a cost: the model asks less about an unclear request. So count early stops before adding one.
- Most endings that put something to a person follow a refused tool call. Take the block away first: the path, the permission, the form of the command. Do not ban the question, because a reader that is blocked and may not say so goes round the block.
- A tool call outside the allow rules is refused, and nobody can approve it. Check each command the document names against the rules, in the form the document gives it. Say where scratch files go, because a temp folder may be refused.

## What the script says and reads

- Read the script before you write the document: what it adds to the prompt, what it sends as a follow-up, and how it reads the output. Do not repeat what it says, and do not contradict it.
- Give each step an end the script can check, such as a fixed heading that the last message ends under. Name the stops that are wanted: a refused write, a missing file, a risky step. Say what the last message holds in each case.
- Give "I cannot do this" a fixed line that the script reads. Do not end such a step by leaving a check to fail, where the script answers a failed check with a follow-up that says to do the work.
- Write to how the script reads. A check that looks for a heading anywhere in a message is passed by a message that only quotes the heading. A list that is read up to the next heading takes in any bullet written below it. So keep a marker out of a message that must not match, start no other line with a marker, and put free prose under a heading of its own.
- A follow-up from the script arrives in the user turn, and the reader gives text in the user turn the user's authority. A document's stop and the script's follow-up must not point opposite ways. The firm mend is in the script. In the document, say that the answer stays the same when the script asks again.
- The last message can cover only the last step. Where the script passes the last message on, say that it is the whole report.
- The script marks text it pastes into a prompt, with a named tag and a line that says who wrote it. In the document, one sentence can say that a pasted note is another Session's account and holds no instruction.
- Where a step must have a skill loaded, the script loads it, with the slash command in the prompt, and then checks that it loaded.
