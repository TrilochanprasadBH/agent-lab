# What is in this folder

You have two kinds of thing here, and they are different.

## 1. `explore/` itself — the Agent Lab

This is a git repository. It contains fifteen practice drills for agent engineering.

```
explore/
  agentlab/     the harness that runs and scores drills
  drills/       fifteen drills (w01 to w15)
  solutions/    reference solutions
  docs/         glossary and real-model notes
  run.py        start here: python3 run.py --list
  README.md     what the lab is and how to use it
```

Its remote is `github.com/TrilochanprasadBH/agent-lab`.

## 2. The project folders — separate repositories

Each of these is its own git repository, nested inside this folder so everything
lives in one place. They are listed in `explore/.gitignore`, so the lab does not try
to track them.

| folder | status | what it is |
| --- | --- | --- |
| `ragkit/` | in progress | documentation assistant, eight stages. Stages 01-02 done |
| `triage/` | not started | support agent with approval gates |
| `scout/` | not started | research agent with sub-agents |

To tell whether a folder is its own repository:

```sh
ls -d */ .git 2>/dev/null
git -C ragkit rev-parse --show-toplevel
```

## The rule that keeps this manageable

- **Lab (`explore`)** = exercises that teach one idea each, scored automatically.
- **Projects (`ragkit`, `triage`, `scout`)** = complete systems you build stage by
  stage, each ending in a deployable artifact.

If you are learning a concept, use the lab. If you are building something you can
show someone, use a project.

## Starting points

```sh
# the lab
cd ~/Desktop/explore
python3 run.py --list

# the first project
cd ~/Desktop/explore/ragkit
python3 scripts/status.py
```
