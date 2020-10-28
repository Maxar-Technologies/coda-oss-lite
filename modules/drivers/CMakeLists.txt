add_subdirectory("boost")
#add_subdirectory("numpy") # this is handled in coda_find_system_dependencies

set(ENABLE_JARS ON CACHE BOOL "include jars in the install")
if (ENABLE_JARS)
    add_subdirectory("jars")
endif()



