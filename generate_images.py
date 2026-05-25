#!/usr/bin/python3

import asyncio
import os
import re

import aiohttp

from github_stats import Stats

################################################################################
# Helper Functions
################################################################################


def generate_output_folder() -> None:
    """
    Create the output folder if it does not already exist
    """
    if not os.path.isdir("generated"):
        os.mkdir("generated")


################################################################################
# Individual Image Generation Functions
################################################################################


async def generate_overview(s: Stats) -> None:
    """
    Generate an SVG badge with summary statistics
    :param s: Represents user's GitHub statistics
    """
    with open("templates/overview.svg", "r") as f:
        output = f.read()

    try:
        name = await s.name if await s.name is not None else "User"
        output = re.sub("{{ name }}", name, output)

        stargazers = await s.stargazers
        output = re.sub(
            "{{ stars }}", f"{stargazers:,}" if stargazers is not None else "0", output
        )

        forks = await s.forks
        output = re.sub(
            "{{ forks }}", f"{forks:,}" if forks is not None else "0", output
        )

        total_contributions = await s.total_contributions
        output = re.sub(
            "{{ contributions }}",
            f"{total_contributions:,}" if total_contributions is not None else "0",
            output,
        )

        lines_changed_data = await s.lines_changed
        if lines_changed_data is not None and len(lines_changed_data) >= 2:
            changed = lines_changed_data[0] + lines_changed_data[1]
            output = re.sub("{{ lines_changed }}", f"{changed:,}", output)
        else:
            output = re.sub("{{ lines_changed }}", "0", output)

        views = await s.views
        output = re.sub(
            "{{ views }}", f"{views:,}" if views is not None else "0", output
        )

        all_repos = await s.all_repos
        output = re.sub(
            "{{ repos }}",
            f"{len(all_repos):,}" if all_repos is not None else "0",
            output,
        )
    except Exception as e:
        print(f"Error generating overview: {str(e)}")
        # Fallback to default values
        output = re.sub("{{ name }}", "User", output)
        output = re.sub("{{ stars }}", "0", output)
        output = re.sub("{{ forks }}", "0", output)
        output = re.sub("{{ contributions }}", "0", output)
        output = re.sub("{{ lines_changed }}", "0", output)
        output = re.sub("{{ views }}", "0", output)
        output = re.sub("{{ repos }}", "0", output)

    generate_output_folder()
    with open("generated/overview.svg", "w") as f:
        f.write(output)


async def generate_languages(s: Stats) -> None:
    """
    Generate an SVG badge with summary languages used
    :param s: Represents user's GitHub statistics
    """
    with open("templates/languages.svg", "r") as f:
        output = f.read()

    progress = ""
    lang_list = ""
    try:
        languages = await s.languages
        if languages is not None:
            sorted_languages = sorted(
                languages.items(),
                reverse=True,
                key=lambda t: t[1].get("size", 0) if t[1] is not None else 0,
            )
            delay_between = 150
            for i, (lang, data) in enumerate(sorted_languages):
                if data is None:
                    continue
                color = data.get("color")
                color = color if color is not None else "#000000"
                ratio = [0.98, 0.02]
                prop = data.get("prop", 0)
                if prop > 50:
                    ratio = [0.99, 0.01]
                if i == len(sorted_languages) - 1:
                    ratio = [1, 0]
                progress += (
                    f'<span style="background-color: {color};'
                    f"width: {(ratio[0] * prop):0.3f}% ;"
                    f'margin-right: {(ratio[1] * prop):0.3f}% ;" '
                    f'class="progress-item"></span>'
                )
                lang_list += f"""
 <li style="animation-delay: {i * delay_between}ms;">
 <svg xmlns="http://www.w3.org/2000/svg" class="octicon" style="fill:{color};"
 viewBox="0 0 16 16" version="1.1" width="16" height="16"><path
 fill-rule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8z"></path></svg>
 <span class="lang">{lang}</span>
 <span class="percent">{prop:0.2f}%</span>
 </li>

 """
        else:
            # If no languages are available, leave the placeholders empty
            pass
    except Exception as e:
        print(f"Error generating languages: {str(e)}")
        # Set empty values in case of error
        progress = ""
        lang_list = ""

    output = re.sub(r"{{ progress }}", progress, output)
    output = re.sub(r"{{ lang_list }}", lang_list, output)

    generate_output_folder()
    with open("generated/languages.svg", "w") as f:
        f.write(output)


################################################################################
# Main Function
################################################################################


async def main() -> None:
    """
    Generate all badges
    """
    access_token = os.getenv("ACCESS_TOKEN")
    if not access_token:
        # access_token = os.getenv("GITHUB_TOKEN")
        raise Exception("A personal access token is required to proceed!")
    user = os.getenv("GITHUB_ACTOR")
    if not user:
        user = os.getenv("USERNAME")  # Fallback to USERNAME if GITHUB_ACTOR is not set
        if not user:
            raise Exception("Username is required to proceed!")

    # Parse excluded repos and languages safely
    exclude_repos_raw = os.getenv("EXCLUDED")
    exclude_repos = None
    if exclude_repos_raw:
        try:
            exclude_repos = {
                x.strip() for x in exclude_repos_raw.split(",") if x.strip()
            }
        except Exception:
            print("Invalid format for EXCLUDED environment variable. Using None.")
            exclude_repos = None

    exclude_langs_raw = os.getenv("EXCLUDED_LANGS")
    exclude_langs = None
    if exclude_langs_raw:
        try:
            exclude_langs = {
                x.strip() for x in exclude_langs_raw.split(",") if x.strip()
            }
        except Exception:
            print("Invalid format for EXCLUDED_LANGS environment variable. Using None.")
            exclude_langs = None

    consider_forked_repos_env = os.getenv("COUNT_STATS_FROM_FORKS")
    consider_forked_repos = bool(
        consider_forked_repos_env
    ) and consider_forked_repos_env.lower() not in ["false", "0", "no"]

    try:
        async with aiohttp.ClientSession() as session:
            s = Stats(
                user,
                access_token,
                session,
                exclude_repos=exclude_repos,
                exclude_langs=exclude_langs,
                consider_forked_repos=consider_forked_repos,
            )
            await asyncio.gather(generate_languages(s), generate_overview(s))
            print("Successfully generated GitHub stats images")
    except Exception as e:
        print(f"Error during generation: {str(e)}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
