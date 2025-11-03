# sbpt

**sbpt** (SuBProjecT) is a tool designed to simplify the sharing of C++ code across multiple projects, eliminating the need to hardcode include paths. It streamlines the process of sharing code by using submodules instead of forcing project-specific file structures. Use the `-h` flag to view the usage instructions.

## Overview

When sharing C++ code, the main challenge is that if you send someone a few code files that depend on other files, you also need to include those dependencies. In the worst case, this leads to the need for the recipient to replicate your entire file structure within their project. While this might work for some, it’s not always ideal—your friend might want to organize their files in their own way.

An alternative is to convert your code into a library that others can link to. However, this introduces additional complexity and maintenance overhead.

**sbpt** solves this problem by enabling the easy sharing of code via **submodules**. Instead of worrying about file structure or converting code into a library, `sbpt` automatically handles dependencies and allows your code to be shared across different projects without the headaches of manual management.

## Features

- **Dynamic Include Management**: Automatically generates include paths and handles dependencies without the need for hardcoded paths, ensuring your code works seamlessly across projects.
- **Simplified Code Sharing**: Share code with others without forcing them to replicate your file structure. `sbpt` allows them to organize their files however they wish.
- **Submodule Integration**: Facilitates the sharing of code using submodules, making it easier to reuse code without creating a full-fledged library.
- **Automatic Generation**: Generates a single `sbpt_generated_includes.hpp` file that handles all necessary includes dynamically, simplifying the integration process for others.

# TODO
- for each subproject have the ability to automatically deduce a version number based on each commit, this can be done through conventional commits, or c++ code anaylsis. Once I can do this I want then add metadata to sbpt.ini about what version a specific subproject depends on, this defines a dependency graph, and the program will try and find a common version number that can be used by all other subprojects trying to use it. Note that using conventional commits might be wrong here because committers can make mistakes, so it'd be better for this system to be automated in a sense. The way I'd automate this is use git and eventually tbx_utils, it would have a function that can extract the api of a hpp file or whatnot, for each commit we can generate the api of it, and then, we can sequentially deduce when the api changes. Once a system like that is in place we know that we can move version numbers in certain ways to resolve the dependency.

## How It Works

When a subproject depends on another, `sbpt` eliminates the need for manual inclusion of dependencies. Instead, it generates the required include paths in a single `sbpt_generated_includes.hpp` file, allowing you to share code without worrying about file structure or complex library setups.

## Usage

To get started, use the `-h` flag to view the available commands and options:

```bash
sbpt -h
```
