import os
import argparse
import configparser
import enum
import subprocess
import requests

from print_utils.main import colored_print, TextColor, BoxPrinter

bp = BoxPrinter()


def find_subprojects(source_dir):
    subprojects = {}
    subproject_paths = {}
    bp.start_box(f"locating subprojects in {source_dir}")
    for root, dirs, files in os.walk(source_dir):
        if "sbpt.ini" in files:
            subproject_name = os.path.basename(root)
            if subproject_name in subprojects:
                raise ValueError(
                    f"Duplicate subproject name found: {subproject_name} in {root} and {subproject_paths[subproject_name]}"
                )
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
            subprojects[subproject_name] = {
                "path": root,
                "dependencies": dependencies,
                "exports": exports,
                "tags": tags,
            }
            subproject_paths[subproject_name] = root
            bp.queue_print(f"found subproject: {subproject_name} at {root}")

    bp.print_box()
    return subprojects


def generate_include_path(subproject_path, dependency_path, export_file):
    relative_path = os.path.relpath(dependency_path, subproject_path)
    return f'#include "{os.path.join(relative_path, export_file)}"'


def write_includes(subprojects):
    bp.start_box("generating sbpt_generated_header.hpp files")
    for subproject, data in subprojects.items():
        bp.queue_print(f"working on {subproject}")
        includes = []
        subproject_path = data["path"]

        # Generate include paths for dependencies
        for dependency in data["dependencies"]:
            bp.queue_print(f"found dependency: {dependency}", 1)
            if dependency in subprojects:
                dependency_path = subprojects[dependency]["path"]
                exports = subprojects[dependency]["exports"]
                if exports == []:
                    bp.queue_print(
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

    bp.print_box()


GITHUB_BASE_URL = "https://raw.githubusercontent.com/cpp-toolbox"


def fetch_file(url):
    """Fetches a file from a given URL and returns its contents if found."""
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        print(f"Failed to fetch file from {url}: {e}")
        return None


def parse_sbpt_ini(ini_content):
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
    return dependencies, tags


def clone_dependency(source_dir, dependency):
    """Handles the process of adding a missing dependency as a git submodule."""
    # Attempt to fetch sbpt.ini if no tags are provided
    sbpt_ini_url = f"{GITHUB_BASE_URL}/{dependency}/main/sbpt.ini"
    sbpt_ini_content = fetch_file(sbpt_ini_url)

    print(sbpt_ini_content)

    tags = []
    if sbpt_ini_content:
        _, tags = parse_sbpt_ini(sbpt_ini_content)
        print(f"Fetched tags for '{dependency}' from sbpt.ini: {tags}")
    else:
        print(f"No sbpt.ini file found for '{dependency}'. Proceeding without tags.")

    # Suggest a tag-based directory if tags are available
    tag_name = tags[0] if tags else None
    suggested_dir = (
        os.path.join(source_dir, tag_name, dependency)
        if tag_name
        else os.path.join(source_dir, dependency)
    )

    # Offer the tag-based directory as a suggestion
    if tag_name:
        use_tag_dir = (
            input(
                f"Would you like to add it under the tag '{tag_name}' in '{suggested_dir}'? (y/n): "
            )
            .strip()
            .lower()
        )
        if use_tag_dir == "y":
            destination_dir = suggested_dir
        else:
            # Prompt for a custom directory if the user doesn't want to use the tag
            destination_dir = input(
                f"Enter a custom directory for '{dependency}' (or press enter to use '{source_dir}'): "
            ).strip() or os.path.join(source_dir, dependency)
    else:
        # Directly prompt for a directory if no tag is available
        destination_dir = input(
            f"Where would you like to store the missing dependency '{dependency}'? "
        ).strip() or os.path.join(source_dir, dependency)

    # Ensure the parent directory exists
    os.makedirs(os.path.dirname(destination_dir), exist_ok=True)

    # Construct the GitHub repository URL based on the assumed naming convention
    clone_url = f"git@github.com:cpp-toolbox/{dependency}.git"
    print(
        f"Adding '{dependency}' as a submodule from '{clone_url}' into '{destination_dir}'..."
    )

    # Add the submodule
    subprocess.run(["git", "submodule", "add", clone_url, destination_dir])

    print(f"Dependency '{dependency}' added as a submodule at '{destination_dir}'.")
    return destination_dir


def sbpt_init(source_dir):
    subprojects = find_subprojects(source_dir)
    subproject_names = list(subprojects.keys())

    cloned_missing_dependencies = False

    bp.start_box("checking if dependencies are satisfied")
    for subproject_name in subproject_names:
        data = subprojects[subproject_name]
        bp.queue_print(f"verifying {subproject_name}")

        for dependency in data["dependencies"]:
            if dependency not in subprojects:
                bp.queue_print(
                    f"dependency '{dependency}' is missing for subproject '{subproject_name}'.",
                    1,
                )
                dependency_path = clone_dependency(source_dir, dependency)
                cloned_missing_dependencies = True

                # Add the cloned subproject to the dictionary
                subprojects[dependency] = {
                    "path": dependency_path,
                    "dependencies": [],  # Load actual dependencies if needed
                    "exports": [],  # Load actual exports if needed
                }
                bp.queue_print(f"subproject {dependency} added.", 2)

    bp.print_box()

    write_includes(subprojects)

    if cloned_missing_dependencies:
        colored_print(
            "warning, there were missing dependencies just cloned in thus we have to setup again, starting that now",
            TextColor.YELLOW,
        )
        sbpt_init(
            source_dir
        )  # recursion bottoms out so long as your dependency chain doesn't have loops


def sbpt_list(source_dir):
    subprojects = find_subprojects(source_dir)
    for subproject, data in subprojects.items():
        print(f"Subproject: {subproject}, Path: {data['path']}")


def sbpt_create(target_dir):
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


def main():
    help_text = """
    sbpt is a project which allows programmers to re-use C++ code in multiple projects easily without having to use a complex system to handle this.
    When a subproject depends on another, usually one has to use an #include to the correct location, so that if that information was stored in the
    project it would break when included in a new project. sbpt dynamically loads in these includes through a `sbpt_generated_includes.hpp` file so
    that they can be loaded into any project and still work.

    Usage:
      sbpt --init <source_dir>
      sbpt --list <source_dir>

    The `sbpt.ini` file format:
      [subproject]
      dependencies = comma,separated,list,of,dependencies
      export = comma,separated,list,of,header,files,to,export
    """

    # Create the argument parser
    parser = argparse.ArgumentParser(
        description="Manage C++ subprojects (sbpts)",
        epilog=help_text,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("source_dir", type=str, help="Run sbpt setup in this directory")

    parser.add_argument(
        "--list",
        metavar="SOURCE_DIR",
        type=str,
        help="List subprojects in the specified source directory",
    )

    parser.add_argument(
        "--create",
        action="store_true",
        help="Create a new subproject in the specified source_dir",
    )

    # Parse the arguments
    args = parser.parse_args()

    # Handle the commands based on provided arguments
    if args.create:
        sbpt_create(args.source_dir)
    elif args.list:
        sbpt_list(args.list)
    elif args.source_dir:
        sbpt_init(args.source_dir)
        colored_print("subprojects successfully configured", TextColor.GREEN)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
