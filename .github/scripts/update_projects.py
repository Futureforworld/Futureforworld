import json
import os
import re
import sys
import urllib.request
import urllib.error

OWNER = "Futureforworld"
README = "README.md"
START = "<!-- AUTO-PROJECTS:START -->"
END = "<!-- AUTO-PROJECTS:END -->"
TOKEN = os.getenv("GITHUB_TOKEN")

def github_get(url):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "Futureforworld-Portfolio-Automation",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"

    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))

def get_repositories():
    repositories = []
    page = 1

    while True:
        url = (
            f"https://api.github.com/users/{OWNER}/repos"
            f"?type=owner&sort=created&direction=desc"
            f"&per_page=100&page={page}"
        )
        batch = github_get(url)
        repositories.extend(batch)

        if len(batch) < 100:
            break
        page += 1

    return repositories

def get_site(repo):
    homepage = (repo.get("homepage") or "").strip()

    if homepage:
        return homepage

    if repo.get("has_pages"):
        url = (
            f"https://api.github.com/repos/"
            f"{OWNER}/{repo['name']}/pages"
        )
        try:
            pages = github_get(url)
            return pages.get("html_url", "")
        except urllib.error.HTTPError as error:
            if error.code not in (404, 403):
                raise

    return ""

def main():
    with open(README, "r", encoding="utf-8-sig") as file:
        original = file.read()

    base = original

    if START in base and END in base:
        before, rest = base.split(START, 1)
        _, after = rest.split(END, 1)
        base = before.rstrip() + "\n\n" + after.lstrip()

    already_linked = set(re.findall(
        r"https?://github\.com/" + re.escape(OWNER)
        + r"/([^/\s)#]+)",
        base,
        flags=re.IGNORECASE
    ))
    already_linked.add(OWNER.lower())

    repositories = get_repositories()
    websites = []
    source_only = []

    for repo in repositories:
        if repo.get("private"):
            continue

        name = repo.get("name", "")
        if not name or name.lower() in already_linked:
            continue

        description = (
            repo.get("description")
            or "Repositório público no GitHub."
        )
        description = " ".join(description.replace("|", "\\|").split())

        language = repo.get("language") or "Tecnologia não informada"
        site = get_site(repo)

        if site:
            websites.append(
                f"- **[{name}]({site})**  {description} "
                f"[Código-fonte]({repo['html_url']})  {language}"
            )
        else:
            source_only.append(
                f"- [{name}]({repo['html_url']})  "
                f"{description}  {language}"
            )

    lines = [
        "##  Projetos com demonstração online",
        "",
        "Projetos com site ou demonstração publicada.",
        ""
    ]

    lines.extend(websites or ["_Nenhum novo site identificado até o momento._"])

    lines.extend([
        "",
        "##  Outros repositórios públicos",
        "",
        "Projetos disponíveis para consulta do código-fonte.",
        ""
    ])

    lines.extend(source_only or ["_Todos os repositórios já estão destacados acima._"])

    generated = START + "\n" + "\n".join(lines) + "\n" + END
    updated = base.rstrip() + "\n\n" + generated + "\n"

    if updated != original:
        with open(README, "w", encoding="utf-8") as file:
            file.write(updated)
        print(
            f"Vitrine atualizada: {len(websites)} projeto(s) com site "
            f"e {len(source_only)} somente com código."
        )
    else:
        print("A vitrine já está atualizada.")

if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"Erro ao atualizar a vitrine: {error}", file=sys.stderr)
        sys.exit(1)
