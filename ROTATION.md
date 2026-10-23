# Rotation

Goal: finish repos one at a time, then swap in new ones, with little hand-holding.

## Repos in rotation
| Repo | Owner | Status |
|------|-------|--------|
| Lord-sidious/PickUpSticks2316 | Lord-sidious | Active (tracker: #3) |
| Insid88/Pocket-change- | Insid88 | Queued |
| Insid88/Dixie-bound (confirm name) | Insid88 | Queued |

## How it works
1. Each repo has one tracker issue ("Repairing" = #3 here) with small child issues labeled `Part of #N`.
2. Pick the oldest unassigned open child issue, assign yourself, open a PR that says `Closes #<issue>`.
3. Stuck? Comment on the issue with `blocked:` and what you need. The owner reads these and answers.
4. When a tracker has no open children, mark the repo Done in the table above and promote the next Queued repo to Active.

## Automation
`.github/workflows/rotation.yml` runs daily and comments on the tracker with open, blocked and next-up issues. It only reports; it never closes or merges anything.
