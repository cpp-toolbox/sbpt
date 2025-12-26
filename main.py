import os
import argparse
import configparser
import enum
import subprocess
import requests
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple, List
import user_input
from user_input.main import *
from print_utils.main import colored_print, TextColor, BoxPrinter

KNOWN_REPOS_FILE = "known_repos.txt"

bp = BoxPrinter()


# startfold known repos
def refresh_and_save_known_repos():
    print("Fetching public repositories from the cpp-toolbox organization...")
    url = "https://api.github.com/orgs/cpp-toolbox/repos"
    headers = {"Accept": "application/vnd.github.v3+json"}

    repos = []
    page = 1

    while True:
        response = requests.get(
            url, headers=headers, params={"page": page, "per_page": 100}
        )
        if response.status_code != 200:
            print(f"Failed to retrieve repositories: {response.status_code}")
            break

        data = response.json()
        if not data:
            break

        repos.extend(data)
        page += 1

    # Save for future searches
    with open(KNOWN_REPOS_FILE, "w") as f:
        for r in repos:
            name = r.get("name", "")
            ssh_url = r.get("ssh_url", "")
            f.write(f"{name}|{ssh_url}\n")

    print(f"Saved {len(repos)} repositories to {KNOWN_REPOS_FILE}")


def load_known_repos() -> List:
    """returns a json thing the format is defined by however the above function gets it"""
    if not os.path.exists(KNOWN_REPOS_FILE):
        print("known_repos.txt does not exist. Creating it now")
        refresh_and_save_known_repos()

    repos = []
    with open(KNOWN_REPOS_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if not line or "|" not in line:
                continue
            name, ssh_url = line.split("|", 1)
            repos.append({"name": name, "ssh_url": ssh_url})

    return repos


# endfold


def find_subprojects(target_dir: str) -> Dict[str, Dict]:
    "looks in the directory recursively to find all existing subprojects"
    subprojects = {}
    subproject_paths = {}
    bp.start_box(f"locating subprojects in {target_dir}")
    for root, dirs, files in os.walk(target_dir):
        if "sbpt.ini" in files:
            subproject_name = os.path.basename(root)
            if subproject_name in subprojects:

                already_existing_subproject = subprojects[subproject_name]
                existing_path = already_existing_subproject["path"]

                print(
                    f"Duplicate subproject name found: {subproject_name} in {root} and {subproject_paths[subproject_name]}"
                )
                if len(root) < len(existing_path):
                    print(
                        f"we are replacing the one located at {existing_path} with the one located at {root} because the path is smaller (this is an arbitrary choice)"
                    )
                else:
                    print(
                        f"we are skipping the one located at {root} and continuing to use the one located at {existing_path} because the path is longer (this is an arbitrary choice)"
                    )
                    continue
            #     raise ValueError(
            #         f"Duplicate subproject name found: {subproject_name} in {root} and {subproject_paths[subproject_name]}"
            #     )
            config = configparser.ConfigParser()
            config.read(os.path.join(root, "sbpt.ini"))
            dependencies = [
                dep.strip()
                for dep in config.get("subproject", "dependencies", fallback="").split(
                    ","
                )
                if dep.strip()
            ]
            exports = [
                exp.strip()
                for exp in config.get("subproject", "export", fallback="").split(",")
                if exp.strip()
            ]
            tags = [
                tag.strip()
                for tag in config.get("subproject", "tags", fallback="").split(",")
                if tag.strip()
            ]
            # TODO: just makes this a class.
            subprojects[subproject_name] = {
                "path": root,
                "dependencies": dependencies,
                "exports": exports,
                "tags": tags,
            }
            subproject_paths[subproject_name] = root
            bp.print_line(f"found subproject: {subproject_name} at {root}")

    bp.end_box()
    return subprojects


# startfold includes


def generate_include_path(subproject_path, dependency_path, export_file):
    relative_path = os.path.relpath(dependency_path, subproject_path)
    return f'#include "{os.path.join(relative_path, export_file)}"'


def write_includes(subprojects):
    bp.start_box("generating sbpt_generated_header.hpp files")
    for subproject, data in subprojects.items():
        bp.print_line(f"working on {subproject}")
        includes = []
        subproject_path = data["path"]

        # Generate include paths for dependencies
        for dependency in data["dependencies"]:
            bp.print_line(f"found dependency: {dependency}", 1)
            if dependency in subprojects:
                dependency_path = subprojects[dependency]["path"]
                exports = subprojects[dependency]["exports"]
                if exports == []:
                    bp.print_line(
                        "warning, this dependency didn't have an export, this will cause a problem when generating the headers"
                    )
                for export_file in exports:
                    include_path = generate_include_path(
                        subproject_path, dependency_path, export_file
                    )
                    includes.append(include_path)
            else:
                error_msg = (
                    f"Error: Dependency {dependency} not found for subproject {subproject}. "
                    "Make sure to clone all the subprojects' dependencies. Running --init can help you sort this out easily."
                )
                colored_print(error_msg, TextColor.RED)

        # Write the generated includes to 'sbpt_generated_includes.hpp'
        include_file_name = "sbpt_generated_includes.hpp"
        include_file_path = os.path.join(subproject_path, include_file_name)
        with open(include_file_path, "w") as include_file:
            include_file.write("\n".join(includes))

        # Handle .gitignore file: create it only if it does not already exist
        gitignore_file_path = os.path.join(subproject_path, ".gitignore")
        if not os.path.exists(gitignore_file_path):
            with open(gitignore_file_path, "w") as gitignore_file:
                gitignore_file.write(".gitignore\n")
                gitignore_file.write(include_file_name)
            # print(f"Generated includes and .gitignore for subproject: {subproject}")
        else:
            pass
            # print(f".gitignore already exists for subproject: {subproject}. Skipping .gitignore creation to avoid overwriting.")

    bp.end_box()


# endfold


RAW_GITHUB_BASE_URL = "https://raw.githubusercontent.com/cpp-toolbox"
GITHUB_BASE_URL = "https://github.com/cpp-toolbox/"


def fetch_file(url: str) -> Optional[str]:
    """Fetches a file from a given URL and returns its contents if found."""
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        print(f"Failed to fetch file from {url}: {e}")
        return None


@dataclass
class SbptIniFile:
    subproject_name: str = ""
    dependencies: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)


def parse_sbpt_ini(ini_content: str, submodule_name: str) -> SbptIniFile:
    """Parses sbpt.ini content to extract dependencies and tags."""
    config = configparser.ConfigParser()
    config.read_string(ini_content)
    dependencies = [
        dep.strip()
        for dep in config.get("subproject", "dependencies", fallback="").split(",")
        if dep.strip()
    ]
    tags = [
        tag.strip()
        for tag in config.get("subproject", "tags", fallback="").split(",")
        if tag.strip()
    ]

    return SbptIniFile(submodule_name, dependencies, tags)


def get_suggested_dir_to_store_submodule(
    sbpt_ini_file: SbptIniFile, target_dir: str
) -> Optional[str]:
    "Suggests a tag-based directory if tags are available otherwise doesn't"
    tag_name = sbpt_ini_file.tags[0] if sbpt_ini_file.tags else None

    if tag_name:
        return os.path.join(target_dir, tag_name, sbpt_ini_file.subproject_name)
    else:
        return None


def fetch_spbt_ini_file(subproject_name: str) -> Optional[SbptIniFile]:
    sbpt_ini_url = f"{RAW_GITHUB_BASE_URL}/{subproject_name}/main/sbpt.ini"
    sbpt_ini_content = fetch_file(sbpt_ini_url)
    if sbpt_ini_content:
        return parse_sbpt_ini(sbpt_ini_content, subproject_name)
    else:
        return None


def get_sbpt_file_content(subproject_name: str) -> Optional[str]:
    # Attempt to fetch sbpt.ini if no tags are provided
    sbpt_ini_url = f"{RAW_GITHUB_BASE_URL}/{subproject_name}/main/sbpt.ini"
    sbpt_ini_content = fetch_file(sbpt_ini_url)
    return sbpt_ini_content


def is_valid_url(url: str) -> bool:
    try:
        response = requests.head(url, allow_redirects=True, timeout=5)
        # 200-399 are generally OK
        return response.status_code == 200
    except requests.RequestException:
        return False


def interactively_add_subproject_as_submodule(
    target_dir: str, subproject_name: str
) -> Optional[str]:
    """
    Handles the process of adding a missing dependency as a git submodule. returns the location that it was stored at

    Note this function assumes that the subproject name is the name of an existing subproject if it's not then the behavior is unspecified
    """

    github_repo_url = f"{GITHUB_BASE_URL}/{subproject_name}"

    if not is_valid_url(github_repo_url):
        print(
            f"There is no remote subproject with the url {github_repo_url}, there are two options"
        )
        choice = select_option_numerical(
            [
                "Create a local subproject with this name",
                "Stop sbpt to investigate further (perhaps the remote submodule has been removed)",
            ],
        )

        if choice == 1:
            chosen_directory = interactively_select_directory(Path(target_dir))
            create_local_subproject_with_cpp_boilerplate(chosen_directory)
            return chosen_directory

        return None

    print(f"We are about to add the following subproject: {subproject_name}")
    # Attempt to fetch sbpt.ini if no tags are provided
    sbpt_ini_url = f"{RAW_GITHUB_BASE_URL}/{subproject_name}/main/sbpt.ini"
    sbpt_ini_content = fetch_file(sbpt_ini_url)

    sbpt_ini_file = fetch_spbt_ini_file(subproject_name)

    chosen_directory: str = ""

    if sbpt_ini_file == None:
        print(
            f"No sbpt.ini file found for '{subproject_name}'. Proceeding with manual placement, please choose a directory:"
        )
        chosen_directory = interactively_select_directory(Path(target_dir))
    elif sbpt_ini_file.tags == []:
        print(
            f"'{subproject_name}' had a sbpt.ini file but had no tags. Proceeding with manual placement, please choose a directory:"
        )
        chosen_directory = interactively_select_directory(Path(target_dir))
    else:
        first_tag_name = sbpt_ini_file.tags[0]
        suggested_dir = os.path.join(target_dir, first_tag_name, subproject_name)
        user_ok_with_directory = get_yes_no(
            f"We are going to place the subproject here: {suggested_dir}, are you ok with this?"
        )
        if not user_ok_with_directory:
            chosen_directory = interactively_select_directory(Path(target_dir))
        else:
            chosen_directory = suggested_dir

    os.makedirs(os.path.dirname(chosen_directory), exist_ok=True)

    # TODO: remove dependency on cpp-toolbox, but I just dont care until someone else wants to use this as well on a diff repo
    ssh_clone_url = f"git@github.com:cpp-toolbox/{subproject_name}.git"
    print(
        f"Adding '{subproject_name}' as a submodule from '{ssh_clone_url}' into '{chosen_directory}'..."
    )

    # Add the submodule
    subprocess.run(["git", "submodule", "add", ssh_clone_url, chosen_directory])

    # NOTE: this logic is here because by default just adding a submodule doesn't get any recursive submodules
    # subprocess.run(["cd", destination_dir])
    # subprocess.run(["git", "submodule", "update", "--init", "--recursive"])
    # subprocess.run(["cd", "-"])

    print(
        f"Dependency '{subproject_name}' added as a submodule at '{chosen_directory}'."
    )
    return chosen_directory


def sbpt_init(target_dir: str) -> None:
    local_subprojects = find_subprojects(target_dir)
    local_subproject_names = list(local_subprojects.keys())

    cloned_missing_dependencies = False

    bp.start_box("checking if dependencies are satisfied")
    for subproject_name in local_subproject_names:
        data = local_subprojects[subproject_name]
        bp.print_line(f"verifying {subproject_name}")

        for dependency in data["dependencies"]:
            if dependency not in local_subprojects:
                bp.print_line(
                    f"dependency subproject '{dependency}' is missing for subproject '{subproject_name}'.",
                    1,
                )
                dependency_path = interactively_add_subproject_as_submodule(
                    target_dir, dependency
                )

                if dependency_path == None:
                    print("we were unable to process this submodule, stopping now")
                    return None

                cloned_missing_dependencies = True

                # Add the cloned subproject to the dictionary
                local_subprojects[dependency] = {
                    "path": dependency_path,
                    "dependencies": [],  # Load actual dependencies if needed
                    "exports": [],  # Load actual exports if needed
                }
                bp.print_line(f"subproject {dependency} added.", 2)

    bp.end_box()

    write_includes(local_subprojects)

    if cloned_missing_dependencies:
        colored_print(
            "warning, there were missing dependencies just cloned in thus we have to setup again, starting that now",
            TextColor.YELLOW,
        )
        sbpt_init(
            target_dir
        )  # recursion bottoms out so long as your dependency chain doesn't have loops


def list_existing_subproject_in_directory_recursively(target_dir: str) -> None:
    subprojects = find_subprojects(target_dir)
    for subproject, data in subprojects.items():
        print(f"Subproject: {subproject}, Path: {data['path']}")


def create_local_subproject_with_cpp_boilerplate(target_dir: str) -> None:
    """Creates a new subproject directory with boilerplate files."""
    os.makedirs(target_dir, exist_ok=True)

    subproject_name = os.path.basename(os.path.normpath(target_dir))
    header_file_name = f"{subproject_name}.hpp"
    source_file_name = f"{subproject_name}.cpp"
    header_path = os.path.join(target_dir, header_file_name)
    source_path = os.path.join(target_dir, source_file_name)
    ini_path = os.path.join(target_dir, "sbpt.ini")

    # Create a C-style include guard name, e.g. "MY_NEW_SUBPROJECT_HPP"
    guard_name = f"{subproject_name.upper()}_HPP"
    guard_name = guard_name.replace("-", "_").replace(" ", "_")

    # Create header file
    if not os.path.exists(header_path):
        with open(header_path, "w") as header_file:
            header_file.write(
                f"#ifndef {guard_name}\n"
                f"#define {guard_name}\n\n"
                f"// {subproject_name} declarations go here\n\n"
                f"#endif // {guard_name}\n"
            )
        colored_print(f"Created {header_path}", TextColor.GREEN)
    else:
        colored_print(f"{header_path} already exists, skipping.", TextColor.YELLOW)

    # Create source file
    if not os.path.exists(source_path):
        with open(source_path, "w") as source_file:
            source_file.write(
                f'#include "{header_file_name}"\n\n'
                f"// {subproject_name} definitions go here\n"
            )
        colored_print(f"Created {source_path}", TextColor.GREEN)
    else:
        colored_print(f"{source_path} already exists, skipping.", TextColor.YELLOW)

    # Create sbpt.ini file
    if not os.path.exists(ini_path):
        with open(ini_path, "w") as ini_file:
            ini_file.write("[subproject]\n")
            ini_file.write(f"export = {header_file_name}\n")
            ini_file.write("dependencies = \n")
            ini_file.write("tags = \n")
        colored_print(f"Created {ini_path}", TextColor.GREEN)
    else:
        colored_print(f"{ini_path} already exists, skipping.", TextColor.YELLOW)

    colored_print(
        f"Subproject '{subproject_name}' created successfully.", TextColor.CYAN
    )


def interactively_select_subproject_name() -> Optional[str]:
    "returns the name of the repository as string eg) periodic_signal"
    repos = load_known_repos()
    if not repos:
        return None

    while True:
        search_keyword = input("Enter a keyword to search for repositories: ").strip()
        if not search_keyword:
            continue

        matching_repos = [
            r for r in repos if search_keyword.lower() in r["name"].lower()
        ]

        if not matching_repos:
            print("No matching repositories found.")
            continue

        print("\nMatching repositories:")
        for i, repo in enumerate(matching_repos):
            print(f"{i+1}: {repo['name']} - {repo['ssh_url']}")

        choice = input(
            "Enter the number to select a repo, or 'n' to search again: "
        ).strip()
        if choice.lower() == "n":
            continue

        try:
            idx = int(choice) - 1
            if idx < 0 or idx >= len(matching_repos):
                print("Invalid choice.")
                continue
        except ValueError:
            print("Invalid input.")
            continue

        selection = matching_repos[idx]
        print(f"\nSelected: {selection['name']} -> {selection['ssh_url']}")
        return selection["name"]


def main():
    parser = argparse.ArgumentParser(
        description="sbpt — Manage reusable C++ subprojects.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser(
        "init",
        help="Initialize sbpt configuration in a target directory.",
        description=(
            "Initialize sbpt in the given target directory.\n"
            "This recursively scans for subprojects, generates sbpt_generated_includes.hpp, "
            "and configures dependencies."
        ),
    )
    init_parser.add_argument(
        "target_dir",
        help="Directory to initialize (imporant since this command is recursive)",
    )

    list_parser = subparsers.add_parser(
        "list",
        help="List sbpt subprojects in a directory.",
        description="List all found subprojects in the specified directory.",
    )
    list_parser.add_argument("target_dir", help="Directory to scan for subprojects.")

    create_parser = subparsers.add_parser(
        "create",
        help="Create a new subproject.",
        description=(
            "Create a new subproject inside the given directory. "
            "This generates a sbpt.ini template and required structure."
        ),
    )
    create_parser.add_argument("target_dir", help="Target directory.")

    refresh_parser = subparsers.add_parser(
        "refresh-known-repos",
        help="Update known_repos.txt by downloading cpp-toolbox public repositories.",
        description="Refresh the known repositories file from the remote cpp-toolbox list.",
    )

    add_parser = subparsers.add_parser(
        "add",
        help="Interactively search and add a known repository as a subproject.",
        description="Runs an interactive fuzzy search and adds a selected subproject.",
    )
    add_parser.add_argument(
        "target_dir",
        help="The directory you want to run this command in the context of",
    )

    args = parser.parse_args()

    if args.command == "init":
        sbpt_init(args.target_dir)
        colored_print("subprojects successfully configured", TextColor.GREEN)

    elif args.command == "list":
        list_existing_subproject_in_directory_recursively(args.target_dir)

    elif args.command == "create":
        create_local_subproject_with_cpp_boilerplate(args.target_dir)

    elif args.command == "refresh-known-repos":
        refresh_and_save_known_repos()

    elif args.command == "add":
        selected_subproject_name = interactively_select_subproject_name()
        if selected_subproject_name:
            interactively_add_subproject_as_submodule(
                args.target_dir, selected_subproject_name
            )
        else:
            print("unable to select a repo, please try again")


if __name__ == "__main__":
    main()
