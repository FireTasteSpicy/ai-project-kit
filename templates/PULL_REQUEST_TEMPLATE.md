<!--
  Standard structure for AI-assisted changes, so reviewers judge consistently and the
  human owns the semantic call. Place at your host's path:
    GitHub → .github/PULL_REQUEST_TEMPLATE.md
    GitLab → .gitlab/merge_request_templates/Default.md
-->

## What changed
<!-- One-paragraph summary. What and where. -->

## Source of truth
<!-- The rule / spec / reference this implements. Cite source lines where relevant
     (e.g. legacy/foo.sas:6320). -->

## Verification
- [ ] Tests + lint + typecheck green
- [ ] Reference/oracle match within agreed tolerance
- [ ] Definition of done (AGENTS.md §9) satisfied
<!-- Paste the diff SUMMARY only — structure/aggregates/pass-fail, never raw data values. -->

```
<oracle diff summary here>
```

## Assumptions & rule gaps
<!-- Anything the spec was silent on and how it was resolved. Link any escalation.
     Copy unresolved gaps into docs/ai/decision-log.md. -->

## Risk / blast radius
<!-- What else could this affect, and what you checked to confirm it didn't. -->
