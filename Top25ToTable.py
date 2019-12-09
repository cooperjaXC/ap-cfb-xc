#!/usr/bin/env python

""" Prints the AP XC results in a table format to easily paste into Excel """

import pandas

import Top25InPython

# FYI: Article Dad sent about auto import of tables from html via pandas:
#   https://medium.com/@ageitgey/quick-tip-the-easiest-way-to-grab-data-out-of-a-web-page-in-python-7153cecfca58

print("-------------PANDAS----------------")
og_dict = pandas.DataFrame.from_dict(Top25InPython.fourscoredict.items())

print(og_dict.to_string(index=False))

# Get data into copy-able format for transfer to excel.
# Subset the Power 5
#   Do this in Team_Conf_Organ.py to reference in other downstream processes.
# Import the Power 5 data frame into excel/csv. Write this to the temp folder(?) & Replace the previous edition.
#   os.remove, etc.
# Or, just read the data frame without writing it to an intermediate file and figure out how to open the APXC.xls file.
#   *** Make a copy of the AP XC xls file before tampering with writing xls files.
#   Remember the package Sean used at ORNL to write the important field finder results. xlsxwriter
pd_conferenceptsdict = pandas.DataFrame.from_dict(
    Top25InPython.conferencepointsdict.items()
)
allptscol = "allpts"
confcol = "conference"
pd_conferenceptsdict.columns = [confcol, allptscol]
pd_pointsexploded = pandas.concat(
    [
        pd_conferenceptsdict.drop([allptscol], axis=1),
        pd_conferenceptsdict[allptscol].apply(pandas.Series),
    ],
    axis=1,
)
# pandas.concat([pd_conferenceptsdict.drop([allptscol], axis=1),
#                pandas.DataFrame(pd_conferenceptsdict[allptscol].tolist())], axis=1)

# # Number of columns with points (excludes conference col) # May not need
# columnswithpoints=len(pd_pointsexploded.columns) - 1

# Rename columns to start with 1 indicating place finish like an XC results sheet.
newcolnames = [confcol]
for cl in pd_pointsexploded.columns:
    if str(cl).isdigit():
        # print(cl, cl+1)
        newcolnames.append(cl + 1)
# print(newcolnames)
pd_pointsexploded.columns = newcolnames
# print(pd_pointsexploded)

# Set a new index with the conferences as the index
pd_newidx = pd_pointsexploded.copy()
pd_newidx = pd_newidx.set_index(["conference"])

pd_transposed = pd_newidx.transpose()
print(pd_transposed.to_string(index=False))

# Dictionary to copy to excel
powerfive_tocopy = pd_transposed[
    [
        "SEC",
        "ACC",
        "Big Ten",
        "Big XII",
        "Pac 12"
        # For 2019, the AAC is included in this. Comment out if irrelevant.
        ,
        "American",
    ]
]
# print(ng with leading zeros so excel's text import wizard will work correctly.)
#   datasciencemadesimple.com/add-leading-preceding-zeros-python/
copycolumns = powerfive_tocopy.columns
for cll in copycolumns:
    # # print(cll)
    # Put leading 0s on each val till len(item) = 4
    #   This min num of chars includes decimals & d point.
    #   4 chosen because rankings rarely get above 40 & only decimal pt val could = .5 in a even # of teams tie
    # # print(powerfive_tocopy[cll].apply(lambda x: '{0:0>4}'.format(x)))
    powerfive_tocopy[cll] = powerfive_tocopy[cll].apply(lambda x: "{0:0>4}".format(x))

# Commented out for 2019; see "power 6" below
print(powerfive_tocopy.to_string(index=False))
# Auto copy this to the clipboard for pasting in Excel without row indexes or column headers
#   Separate by tab in the Excel text importer
powerfive_tocopy.to_clipboard(index=False, header=False, sep=" ")
