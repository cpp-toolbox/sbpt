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

## How It Works

When a subproject depends on another, `sbpt` eliminates the need for manual inclusion of dependencies. Instead, it generates the required include paths in a single `sbpt_generated_includes.hpp` file, allowing you to share code without worrying about file structure or complex library setups.

## Usage

To get started, use the `-h` flag to view the available commands and options:

```bash
sbpt -h
```
