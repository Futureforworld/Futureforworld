import json
import os
import re
import sys
import urllib.request
import urllib.error
from urllib.parse import urlsplit

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

def validate_site(url):
    if not url:
        return ""

    url = url.strip()
    parsed = urlsplit(url)

    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return ""

    host = parsed.hostname.lower()

    blocked_hosts = {
        "github.com",
        "www.github.com",
        "api.github.com",
        "raw.githubusercontent.com",
        "gist.github.com"
    }

    if host in blocked_hosts or host.endswith(".github.com"):
        return ""

    try:
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 PortfolioChecker"},
            method="GET"
        )
        with urllib.request.urlopen(request, timeout=15) as response:
            if 200 <= response.status < 400:
                return response.geturl()
    except (urllib.error.URLError, TimeoutError, ValueError):
        return ""

    return ""

def get_site(repo):
    homepage = validate_site(repo.get("homepage", ""))

    if homepage:
        return homepage

    if repo.get("has_pages"):
        url = (
            f"https://api.github.com/repos/"
            f"{OWNER}/{repo['name']}/pages"
        )
        try:
            pages = github_get(url)
            return validate_site(pages.get("html_url", ""))
        except (urllib.error.HTTPError, urllib.error.URLError):
            return ""

    return ""

def extract_manual_projects(text):
    pattern = (
        r"https?://github\.com/"
        + re.escape(OWNER)
        + r"/([^/?#\s)]+)"
    )
    return {
        name.lower()
        for name in re.findall(pattern, text, flags=re.IGNORECASE)
    }

def add_demo_to_manual_links(text, repo_name, site):
    pattern = re.compile(
        r"(\[[^\]]+\]\(https://github\.com/"
        + re.escape(OWNER)
        + r"/"
        + re.escape(repo_name)
        + r"\))",
        flags=re.IGNORECASE
    )

    def replace_link(match):
        following = text[match.end():match.end() + 250]
        if "Demonstração online" in following:
            return match.group(1)
        return match.group(1) + f"   [Demonstração online]({site})"

    return pattern.sub(replace_link, text)

def main():
    with open(README, "r", encoding="utf-8-sig") as file:
        original = file.read()

    base = original

    if START in base and END in base:
        before, remainder = base.split(START, 1)
        _, after = remainder.split(END, 1)
        base = before.rstrip() + "\n\n" + after.lstrip()

    manual_projects = extract_manual_projects(base)
    repositories = get_repositories()

    websites = []
    source_only = []
    demos_added = 0

    for repo in repositories:
        if repo.get("private"):
            continue

        name = repo.get("name", "")
        if not name or name.lower() == OWNER.lower():
            continue

        site = get_site(repo)

        if name.lower() in manual_projects:
            if site:
                new_base = add_demo_to_manual_links(base, name, site)
                if new_base != base:
                    demos_added += 1
                    base = new_base
            continue

        description = (
            repo.get("description")
            or "Repositório público no GitHub."
        )
        description = " ".join(
            description.replace("|", "\\|").split()
        )
        language = repo.get("language") or "Tecnologia não informada"

        if site:
            websites.append(
                f"- **[{name}]({site})**  {description} "
                f" [Código-fonte]({repo['html_url']})  {language}"
            )
        else:
            source_only.append(
                f"- [{name}]({repo['html_url']})  "
                f"{description}  {language}"
            )

    lines = [
        "##  Projetos com demonstração online",
        "",
        "Projetos com endereço de demonstração validado.",
        ""
    ]

    lines.extend(
        websites or ["_Nenhum outro site validado no momento._"]
    )

    lines.extend([
        "",
        "##  Outros repositórios públicos",
        "",
        "Projetos disponíveis para consulta do código-fonte.",
        ""
    ])

    lines.extend(
        source_only or ["_Nenhum outro repositório para listar._"]
    )

    generated = START + "\n" + "\n".join(lines) + "\n" + END
    updated = base.rstrip() + "\n\n" + generated + "\n"

    if updated != original:
        with open(README, "w", encoding="utf-8") as file:
            file.write(updated)

    print("Resumo da atualização:")
    print(f"Sites validados em novos projetos: {len(websites)}")
    print(f"Outros repositórios: {len(source_only)}")
    print(f"Destaques manuais com demonstração adicionada: {demos_added}")

    if updated == original:
        print("README já estava atualizado.")

if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"Erro ao atualizar a vitrine: {error}", file=sys.stderr)
        sys.exit(1)
