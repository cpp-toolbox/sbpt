import os
import argparse
import configparser

def find_subprojects(source_dir):
    subprojects = {}
    subproject_paths = {}
    print(f"Searching for subprojects in {source_dir}...")
    for root, dirs, files in os.walk(source_dir):
        if 'sbpt.ini' in files:
            subproject_name = os.path.basename(root)
            if subproject_name in subprojects:
                raise ValueError(f"Duplicate subproject name found: {subproject_name} in {root} and {subproject_paths[subproject_name]}")
            config = configparser.ConfigParser()
            config.read(os.path.join(root, 'sbpt.ini'))
            dependencies = [dep.strip() for dep in config.get('subproject', 'dependencies', fallback='').split(',') if dep.strip()]
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
                print(f"Error: Dependency {dependency} not found for subproject {subproject}")

        include_file_name = 'sbpt_generated_includes.hpp'

        include_file_path = os.path.join(subproject_path, include_file_name)
        with open(include_file_path, 'w') as include_file:
            include_file.write('\n'.join(includes))

        gitignore_file_path = os.path.join(subproject_path, '.gitignore')
        with open(gitignore_file_path, 'w') as gitignore_file:
            gitignore_file.write(include_file_name)

        print(f"Generated includes and gitignore for subproject: {subproject}")

def sbpt_initialize(source_dir):
    subprojects = find_subprojects(source_dir)
    write_includes(subprojects)
    print("Initialization complete.")

def sbpt_list(source_dir):
    subprojects = find_subprojects(source_dir)
    for subproject, data in subprojects.items():
        print(f"Subproject: {subproject}, Path: {data['path']}")

def write_help_to_readme(help_text):
    with open('readme.txt', 'w') as readme_file:
        readme_file.write(help_text)

def main():
    help_text = """
    sbpt is a project which allows programmers to re-use C++ code in multiple projects easily without having to use a complex system to handle this.
    When a subproject depends on another, usually one has to use an #include to the correct location, so that if that information was stored in the
    project it would break when included in a new project. sbpt dynamically loads in these includes through a `sbpt_generated_includes.hpp` file so
    that they can be loaded into any project and still work.

    Usage:
      sbpt initialize <source_dir>
      sbpt list <source_dir>

    The `sbpt.ini` file format:
      [subproject]
      dependencies = comma,separated,list,of,dependencies
      export = comma,separated,list,of,header,files,to,export
    """
    parser = argparse.ArgumentParser(description="Manage C++ subprojects.", epilog=help_text, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('command', choices=['initialize', 'list'], help="Command to run")
    parser.add_argument('source_dir', help="Source directory to look for subprojects")
    args = parser.parse_args()

    # Write help text to readme.txt
    write_help_to_readme(help_text)

    if args.command == 'initialize':
        sbpt_initialize(args.source_dir)
    elif args.command == 'list':
        sbpt_list(args.source_dir)

if __name__ == '__main__':
    main()
