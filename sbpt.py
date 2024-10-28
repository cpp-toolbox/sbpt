import os
import argparse
import configparser
import enum

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
            subprojects[subproject_name] = {
                'path': root,
                'dependencies': dependencies,
                'exports': exports
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
        for dependency in data['dependencies']:
            if dependency in subprojects:
                dependency_path = subprojects[dependency]['path']
                for export_file in subprojects[dependency]['exports']:
                    include_path = generate_include_path(subproject_path, dependency_path, export_file)
                    includes.append(include_path)
            else:
                error_msg = f"Error: Dependency {dependency} not found for subproject {subproject}, be make sure to clone in all the subprojects dependencies"
                colored_print(error_msg, TextColor.RED)

        include_file_name = 'sbpt_generated_includes.hpp'

        include_file_path = os.path.join(subproject_path, include_file_name)
        with open(include_file_path, 'w') as include_file:
            include_file.write('\n'.join(includes))

        gitignore_file_path = os.path.join(subproject_path, '.gitignore')
        with open(gitignore_file_path, 'w') as gitignore_file:
            gitignore_file.write(".gitignore\n")
            gitignore_file.write(include_file_name)

        print(f"Generated includes and gitignore for subproject: {subproject}")


def sbpt_init(source_dir):
    subprojects = find_subprojects(source_dir)
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
