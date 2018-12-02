import pandas

import Top25InPython

print pandas.DataFrame.from_dict(Top25InPython.fourscoredict.items())

# Fix T25 tie issue
# Subset the Power 5
#   Do this in Team_Conf_Organ.py to reference in other downstream processes.
# Import the Power 5 data frame into excel/csv. Write this to the temp folder(?) & Replace the previous edition.
#   os.remove, etc.
# Or, just read the data frame without writing it to an intermediate file and figure out how to open the APXC.xls file.
#   *** Make a copy of the AP XC xls file before tampering with writing xls files.
#   Remember the package Sean used at ORNL to write the important field finder results.
