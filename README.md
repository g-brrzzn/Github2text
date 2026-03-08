# Github2text

Github2text is a Python script that extracts metadata from GitHub repositories and converts it into structured text formats. It's designed to help you back up repository metadata, analyze a user's language stack, or generate a quick text summary of an account's projects.

## Key Features & Output Example

* Fetches repository data (stars, forks, description, topics, visibility).
* Calculates exact code size by programming language across the account.
* Handles rate limits automatically.
* Outputs data in JSON, Markdown, and plain text.

**Example output (`summary.txt`):**

```text
GitHub Account Summary
----------------------
Total repositories: 41
Public repositories: 24
Private repositories: 17

Top languages by code size: C# (442797 bytes), Python (259655 bytes), Java (199259 bytes), C++ (109215 bytes), Jupyter Notebook (50005 bytes)

Top repositories by stars:
- example-game: 5 stars
- java-backend: 3 stars
- grid-app: 3 stars

Most recently pushed repositories:
- awesome-script (pushed: 2026-03-08T18:44:31Z)
- data-pipeline (pushed: 2026-03-07T18:26:22Z)
- private-engine (pushed: 2026-03-05T22:30:43Z)

Repository details:

- example-game | lang=Python | stars=5 | forks=1 | private=False | topics=[game, python, pygame] | A base game built from scratch with Python.
- java-backend | lang=Java | stars=3 | forks=0 | private=False | topics=[java, spring-boot, api] | Web service designed to search and organize data.
- private-engine | lang=C# | stars=0 | forks=0 | private=True | topics=[] | no description

```

*(Truncated for readability. The real output includes all repositories.)*

* * * * *

Usage & Examples
----------------

To get started, clone the repository and install the single requirement (`requests`):

Bash

```
git clone https://github.com/g-brrzzn/Github2text
cd Github2text
pip install -r requirements.txt

```

You can run the script entirely from the command line. The generated files will be saved in a `./github_export_out` folder by default.

**Fetch all repositories (including private) using a token:**

Bash

```
python .\github2text.py --token "ghp_your_token_here"

```

**Fetch public repositories from a specific user:**

Bash

```
python .\github2text.py --username "torvalds"

```

**Specify a custom output directory:**

Bash

```
python .\github2text.py --token "ghp_your_token_here" --output-dir ".\my_backup"

```

### Command-Line Arguments

| **Argument** | **Short** | **Description** |
| --- | --- | --- |
| `--username` | `-u` | The GitHub username to fetch. Required if no token is provided. |
| `--token` | `-t` | Your GitHub Personal Access Token. |
| `--output-dir` | `-o` | The folder path where the generated files will be saved. Default: `./github_export_out` |

* * * * *

Authentication & Fetching Private Repositories
----------------------------------------------

By default, unauthenticated requests can only fetch **public** repositories and are strictly rate-limited by the GitHub API (60 requests per hour).

To fetch your **private repositories** and increase your rate limit to 5,000 requests per hour, you must generate a Personal Access Token (PAT).

**How to generate a token:**

1.  Go to your GitHub settings: **Settings** > **Developer settings** > **Personal access tokens** > **Tokens (classic)**.

2.  Click **Generate new token (classic)**.

3.  Check the **`repo`** scope box (this grants access to read private repository data).

4.  Click **Generate token**.

5.  Copy the token (it begins with `ghp_`) and use it with the `--token` argument.

* * * * *

Generated Outputs
-----------------

The script generates three distinct files per run:

1.  **`data.json`**: The raw, structured dictionary of your repositories. Useful if you want to pipe the data into another database or script.

2.  **`summary.txt`**: A high-level text overview of the account, showing top languages, most starred projects, and a quick one-line summary per repository.

3.  **`report.md`**: A detailed Markdown file where each repository gets its own section containing its URL, language breakdown, open issues, topics, size, and timestamps.
