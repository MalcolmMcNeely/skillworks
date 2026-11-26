# Provider questions

Each question asks about the provider and the model a call uses: the generation call, or an eval judge. These facts change between model releases, so never answer one from memory.

Answer each question that bears on the call from the provider's current docs for that model, and give the URL of the page that answers it. A question the docs do not answer is "not found", with where you looked. Report each answer, with its URL, in the report.

1. **Temperature.** Does the model accept a temperature setting? If it does not, the levers left are the prompt, the model and the model's other settings.
2. **Prefill.** Does the model accept prefill, the start of a reply that the call writes for the model?
3. **Length and count keywords.** Which length and count keywords does structured output reject, such as a longest or shortest text, or a most or fewest items? Does it limit the values a keyword accepts? A keyword it rejects fails the call, so keep it off the reply type and check that limit in code after the call.
4. **Property order.** Does the output keep the schema's property order? Where do required properties fall against optional ones? A property that has to come first, such as a short critique before an eval judge's verdict, depends on both answers.
5. **Reasoning fields.** Can a reply field that is named or framed as reasoning draw a refusal? If it can, name and frame the field for what was decided, such as evidence quoted from the output, and not for how.
6. **Enum case.** Can enum values come back in another case? If they can, code compares them without regard to case.
7. **Refusal field.** Does the reply have a refusal field to check? If it does, code checks it before it reads the reply.
