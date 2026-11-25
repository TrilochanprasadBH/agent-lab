# What is in this folder

Two kinds of thing, and they are different.

## Read these first

| file | what it is |
| --- | --- |
| `AGENTS.md` | the rules: how work is built, graded, written, and committed here |
| `ROADMAP.md` | what exists, the coverage of the 25 topics, and what comes next |
| `WORKSPACE.md` | this file |

`AGENTS.md` is not optional reading. A new session that skips it will produce work that
does not match the rest of the folder.

## 1. `explore/` itself — the Agent Lab

A git repository containing nineteen practice drills for agent engineering.

```
explore/
  agentlab/     the harness that runs and scores drills
  drills/       nineteen drills (w01 to w19)
  solutions/    reference solutions
  docs/         glossary and real-model notes
  run.py        start here: python3 run.py --list
```

Remote: `github.com/TrilochanprasadBH/agent-lab`.

## 2. The project folders — separate repositories

Each is its own git repository, nested here so everything lives in one place. They are
listed in `explore/.gitignore`, so the lab does not try to track them.

| folder | status | what it is | remote |
| --- | --- | --- | --- |
| `ragkit/` | complete | documentation assistant, eight stages | `github.com/TrilochanprasadBH/ragkit` |
| `triage/` | complete | support agent with approval gates | `github.com/TrilochanprasadBH/triage` |
| `scout/` | complete | research agent with read-only sub-agents | `github.com/TrilochanprasadBH/scout` |

To tell whether a folder is its own repository:

```sh
git -C ragkit rev-parse --show-toplevel
```

## The rule that keeps this manageable

- **Lab (`explore`)** — exercises that teach one idea each and are scored automatically.
- **Projects (`ragkit`, `triage`, `scout`)** — complete systems built stage by stage, each
  ending in something deployable and defensible.

Learning a concept: use the lab. Building something to show someone: use a project.

## Starting points

```sh
# the lab
cd ~/Desktop/explore
python3 run.py --list

# the finished project
cd ~/Desktop/explore/ragkit
python3 scripts/status.py

# what to do next
cat ~/Desktop/explore/ROADMAP.md
```
