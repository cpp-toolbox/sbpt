# sbpt
This script allows for c++ files to include eachother as dependencies without hardcoding the path the other. The name sbpt comes from SuBProjecT. Use the -h flag to learn how to use it

  sbpt is a project which allows programmers to re-use C++ code in multiple projects easily without having to use a complex system to handle this.
  When a subproject depends on another, usually one has to use an #include to the correct location, so that if that information was stored in the
  project it would break when included in a new project. sbpt dynamically loads in these includes through a `sbpt_generated_includes.hpp` file so
  that they can be loaded into any project and still work.
