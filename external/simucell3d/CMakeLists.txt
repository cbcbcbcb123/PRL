cmake_minimum_required(VERSION 3.0)

#Use CPP 17
set(CMAKE_CXX_STANDARD 17)


#The name of the project
project(DCM)

#Check if the python bindings should be compiled
if(NOT DEFINED ENABLE_PYTHON_BINDINGS)
    set(ENABLE_PYTHON_BINDINGS FALSE)
endif()

if(ENABLE_PYTHON_BINDINGS)
    message(STATUS "Python bindings enabled")
else()
    message(STATUS "Python bindings disabled")
endif()

if(NOT DEFINED PRL_CELL_ENGINE_BUILD_TESTS)
    set(PRL_CELL_ENGINE_BUILD_TESTS TRUE)
endif()

if(NOT DEFINED PRL_CELL_ENGINE_BUILD_EXECUTABLE)
    set(PRL_CELL_ENGINE_BUILD_EXECUTABLE TRUE)
endif()


#Activate unit testing when this repository is built standalone.
if(PRL_CELL_ENGINE_BUILD_TESTS)
    enable_testing()
endif()

#Contains the external library such as tinyxml (the xml reader)
add_subdirectory(lib)

#Contains the source files (.cpp)
add_subdirectory(src bin) 

#Library containing all the tests to run
if(PRL_CELL_ENGINE_BUILD_TESTS)
    add_subdirectory(test)
endif()

#Create the standalone executable unless the engine is embedded as a library.
if(PRL_CELL_ENGINE_BUILD_EXECUTABLE)
    find_package(OpenMP REQUIRED)
    add_executable(simucell3d main.cpp)
    add_definitions(-DPROJECT_SOURCE_DIR="${PROJECT_SOURCE_DIR}")
    target_link_libraries(simucell3d PUBLIC
        src
        OpenMP::OpenMP_CXX
    )
endif()

#In debog mode, we do not use openMP
if (CMAKE_BUILD_TYPE STREQUAL "Debug")
    message("-- Building in debug mode")
else()
    message("-- Building in release mode")
endif()





