import sys
# Import global defaults
from DefaultSettings import *

# Import local configuration
import os
if "TEES_SETTINGS" in os.environ:
    import imp
    pathname = os.environ["TEES_SETTINGS"]
    imp.load_source("TEESLocalSettings", pathname)
    # import everything from local settings module
    exec "from TEESLocalSettings import *"
    
def setLocal(variable, value, setVariable=True):
    # the settings file must exist and must be in the path
    if not setVariable: # notify only, do not add the variable
        print >> sys.stderr, "Remember to add local setting", str(variable) + "=\"" + str(value) + "\""
        return
    assert "TEES_SETTINGS" in os.environ
    print >> sys.stderr, "Adding local setting", str(variable) + "=" + str(value),
    # define the variable in the current module
    exec (variable + " = '" + str(value) + "'") in globals()
    # read the local settings file
    f = open(os.environ["TEES_SETTINGS"], "rt")
    lines = f.readlines()
    f.close()
    
    # if the variable already exists, change its value
    found = False
    for i in range(len(lines)):
        if lines[i].strip() != "" and lines[i].strip()[0] == "#": # skip comment lines
            continue
        if lines[i].split("=")[0].strip() == variable: # variable definition line
            lines[i] = variable + " = '" + str(value) + "'\n"
            print >> sys.stderr, "(updated existing value)"
            found = True
    # if the variable doesn't exist, add it to the end of the file
    if not found:
        lines.append(variable + " = '" + str(value) + "'\n")
        print >> sys.stderr, "(added variable)"
    
    # write the local settings file
    f = open(os.environ["TEES_SETTINGS"], "wt")
    for line in lines:
        f.write(line)
    f.close()