
    sbpt is a project which allows programmers to re-use C++ code in multiple projects easily without having to use a complex system to handle this.
    When a subproject depends on another, usually one has to use an #include to the correct location, so that if that information was stored in the
    project it would break when included in a new project. sbpt dynamically loads in these includes through a `sbpt_generated_includes.hpp` file so
    that they can be loaded into any project and still work.

    Usage:
      sbpt initialize
      sbpt list

    In order to create a subproject all you have to do is have a directory which contains the relevant files and create a `sbpt.ini` file in its root,
    it follows the following format: 

      [subproject]
      dependencies = comma,separated,list,of,dependencies
      export = comma,separated,list,of,header,files,to,export
    