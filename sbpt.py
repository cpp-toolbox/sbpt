import os
import argparse
import configparser
import enum
import subprocess
import requests

class TextColor(enum.Enum):
    BLACK = 30
    RED = 31
    GREEN = 32
    YELLOW = 33
    BLUE = 34
    MAGENTA = 35
    CYAN = 36
    WHITE = 37
    RESET = 0

def colored_print(text: str, color: TextColor):
    # Use the ANSI escape code for the selected color
    print(f"\033[{color.value}m{text}\033[0m")

def find_subprojects(source_dir):
    subprojects = {}
    subproject_paths = {}
    print(f"Searching for subprojects in {source_dir}...")
    for root, dirs, files in os.walk(source_dir):
        if 'sbpt.ini' in files:
            subproject_name = os.path.basename(root)
            if subproject_name in subprojects:
                raise ValueError(
                    f"Duplicate subproject name found: {subproject_name} in {root} and {subproject_paths[subproject_name]}")
            config = configparser.ConfigParser()
            config.read(os.path.join(root, 'sbpt.ini'))
            dependencies = [dep.strip() for dep in config.get('subproject', 'dependencies', fallback='').split(',') if
                            dep.strip()]
            exports = [exp.strip() for exp in config.get('subproject', 'export', fallback='').split(',') if exp.strip()]
            tags = [tag.strip() for tag in config.get('subproject', 'tags', fallback='').split(',') if tag.strip()]
            subprojects[subproject_name] = {
                'path': root,
                'dependencies': dependencies,
                'exports': exports,
                'tags': tags
            }
            subproject_paths[subproject_name] = root
            print(f"Found subproject: {subproject_name}")
    return subprojects

def generate_include_path(subproject_path, dependency_path, export_file):
    relative_path = os.path.relpath(dependency_path, subproject_path)
    return f'#include "{os.path.join(relative_path, export_file)}"'

def write_includes(subprojects):
    for subproject, data in subprojects.items():
        print(f"Processing subproject: {subproject}")
        includes = []
        subproject_path = data['path']
        
        # Generate include paths for dependencies
        for dependency in data['dependencies']:
            if dependency in subprojects:
                dependency_path = subprojects[dependency]['path']
                for export_file in subprojects[dependency]['exports']:
                    include_path = generate_include_path(subproject_path, dependency_path, export_file)
                    includes.append(include_path)
            else:
                error_msg = (
                    f"Error: Dependency {dependency} not found for subproject {subproject}. "
                    "Make sure to clone all the subprojects' dependencies. Running --init can help you sort this out easily."
                )
                colored_print(error_msg, TextColor.RED)
        
        # Write the generated includes to 'sbpt_generated_includes.hpp'
        include_file_name = 'sbpt_generated_includes.hpp'
        include_file_path = os.path.join(subproject_path, include_file_name)
        with open(include_file_path, 'w') as include_file:
            include_file.write('\n'.join(includes))

        # Handle .gitignore file: create it only if it does not already exist
        gitignore_file_path = os.path.join(subproject_path, '.gitignore')
        if not os.path.exists(gitignore_file_path):
            with open(gitignore_file_path, 'w') as gitignore_file:
                gitignore_file.write(".gitignore\n")
                gitignore_file.write(include_file_name)
            print(f"Generated includes and .gitignore for subproject: {subproject}")
        else:
            print(f".gitignore already exists for subproject: {subproject}. Skipping .gitignore creation to avoid overwriting.")


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
    dependencies = [dep.strip() for dep in config.get('subproject', 'dependencies', fallback='').split(',') if dep.strip()]
    tags = [tag.strip() for tag in config.get('subproject', 'tags', fallback='').split(',') if tag.strip()]
    return dependencies, tags

def clone_dependency(source_dir, dependency):
    """Handles the process of adding a missing dependency as a git submodule."""
    # Attempt to fetch sbpt.ini if no tags are provided
    sbpt_ini_url = f"{GITHUB_BASE_URL}/{dependency}/main/sbpt.ini"
    sbpt_ini_content = fetch_file(sbpt_ini_url)
    
    tags = []
    if sbpt_ini_content:
        _, tags = parse_sbpt_ini(sbpt_ini_content)
        print(f"Fetched tags for '{dependency}' from sbpt.ini: {tags}")
    else:
        print(f"No sbpt.ini file found for '{dependency}'. Proceeding without tags.")
    
    # Suggest a tag-based directory if tags are available
    tag_name = tags[0] if tags else None
    suggested_dir = os.path.join(source_dir, tag_name, dependency) if tag_name else os.path.join(source_dir, dependency)

    # Offer the tag-based directory as a suggestion
    if tag_name:
        use_tag_dir = input(f"Would you like to add it under the tag '{tag_name}' in '{suggested_dir}'? (y/n): ").strip().lower()
        if use_tag_dir == 'y':
            destination_dir = suggested_dir
        else:
            # Prompt for a custom directory if the user doesn't want to use the tag
            destination_dir = input(f"Enter a custom directory for '{dependency}' (or press enter to use '{source_dir}'): ").strip() or os.path.join(source_dir, dependency)
    else:
        # Directly prompt for a directory if no tag is available
        destination_dir = input(f"Where would you like to store the missing dependency '{dependency}'? ").strip() or os.path.join(source_dir, dependency)

    # Ensure the parent directory exists
    os.makedirs(os.path.dirname(destination_dir), exist_ok=True)

    # Construct the GitHub repository URL based on the assumed naming convention
    clone_url = f"git@github.com:cpp-toolbox/{dependency}.git"
    print(f"Adding '{dependency}' as a submodule from '{clone_url}' into '{destination_dir}'...")

    # Add the submodule
    subprocess.run(['git', 'submodule', 'add', clone_url, destination_dir])

    print(f"Dependency '{dependency}' added as a submodule at '{destination_dir}'.")
    return destination_dir

def sbpt_init(source_dir):
    subprojects = find_subprojects(source_dir)

    # Create a static list of subproject names to iterate over
    subproject_names = list(subprojects.keys())

    for subproject_name in subproject_names:
        data = subprojects[subproject_name]
        print(f"Processing subproject: {subproject_name}")

        # Check dependencies and add missing ones
        for dependency in data['dependencies']:
            if dependency not in subprojects:
                print(f"Dependency '{dependency}' is missing for subproject '{subproject_name}'.")
                dependency_path = clone_dependency(source_dir, dependency)

                # Add the cloned subproject to the dictionary
                subprojects[dependency] = {
                    'path': dependency_path,
                    'dependencies': [],  # Load actual dependencies if needed
                    'exports': []  # Load actual exports if needed
                }
                print(f"Subproject {dependency} added.")

    # After ensuring all dependencies are available, write include files
    write_includes(subprojects)
    print("Initialization complete.")

def sbpt_list(source_dir):
    subprojects = find_subprojects(source_dir)
    for subproject, data in subprojects.items():
        print(f"Subproject: {subproject}, Path: {data['path']}")

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
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Add command options
    parser.add_argument(
        '--init',
        metavar='SOURCE_DIR',
        type=str,
        help="Initialize a subproject in the specified source directory"
    )

    parser.add_argument(
        '--list',
        metavar='SOURCE_DIR',
        type=str,
        help="List subprojects in the specified source directory"
    )

    # Parse the arguments
    args = parser.parse_args()

    # Handle the commands based on provided arguments
    if args.init:
        sbpt_init(args.init)
    elif args.list:
        sbpt_list(args.list)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
