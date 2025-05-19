# AGENTS Instructions

This repository contains a copy of the **Automatic Rebase** GitHub Action. The main
logic lives in `entrypoint.sh` which is executed inside the Docker image defined in
`Dockerfile`. The `action.yml` file exposes a single optional input `autosquash` and
points GitHub Actions to use the Dockerfile as the runtime environment.

## Project Layout

```
/
├── 1                 # placeholder file containing a single "1"
├── Dockerfile        # builds an Alpine based image and adds entrypoint.sh
├── LICENSE           # MIT License
├── README.md         # instructions on how to install and use the action
├── action.yml        # GitHub Action metadata
├── entrypoint.sh     # shell script implementing the rebase logic
├── casa/             # empty directory (placeholder)
├── echo/             # empty directory (placeholder)
└── logus/            # empty directory (placeholder)
```

### entrypoint.sh summary

The script performs the following high-level steps:

1. Determine the pull request number either from the triggering event or the
   `PR_NUMBER` environment variable.
2. Use the GitHub API to check if the pull request is rebaseable. It retries
   several times until GitHub returns a definitive answer.
3. Collect the base and head repository information along with user details in
   order to configure git.
4. Configure git credentials using the provided `GITHUB_TOKEN` or a token from
   a user‑specific environment variable (`<user>_TOKEN`).
5. Fetch the base and head branches, perform a rebase (with `--autosquash` when
   the `autosquash` input is `true`), and force‑push the updated branch back to
   the fork.

This logic mirrors the functionality of [cirrus-actions/rebase].

## Usage

See `README.md` for full usage instructions. In short, configure a workflow so
that commenting `/rebase` on a pull request runs this action. A minimal example
is provided in the README.

## Development Notes

- There are no automated tests or dependency managers in this repository.
- The placeholder directories (`casa`, `echo`, `logus`) and the file `1` do not
  affect the action itself; they exist only so Git tracks those paths.
- When modifying the shell script, you can run `bash -n entrypoint.sh` for a
  quick syntax check. There are no other required build steps.

